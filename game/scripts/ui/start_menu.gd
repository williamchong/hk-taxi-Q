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
## **And over a paused drive** (the user's ask): `Main` opens a fresh one with
## `pausing` set on the PAUSE page, over a tree it has paused, so this one
## alone runs — RESUME, HOW TO PLAY, OPTIONS, and the way out of the run. Its
## OPTIONS are the ones a held drive can take (`Q223`): the sound, the
## steering thumb's response, a phone's frame cap. Never the language nor the
## thumbs' sides: each is a new HUD (`Main._renew_hud`), and a HUD readied
## mid-fare would never hear the fare's signals already sent.
##
## **OPTIONS is a list of groups, a page each** (`Q223`, the user's pick):
## SOUND, CONTROLS, DISPLAY, LANGUAGE. A group with nothing in it for this
## device and this menu is not listed (`_groups`), and a list of one is
## skipped for its page.
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
## `--menu-page=<home|play|guide|options|credits|notices|report|record|pause|sound|controls|display|language>`
## opens on that page, so a frame of any sheet is one `drive.sh` run and never a click; the
## report so opened is an empty shift's, and the pause `Main`'s over the car on
## the start line. `--menu-sample=on` fills the 成績表 on any of them for a frame,
## and a run naming either flag saves nothing to the record (`Main`).
##
## ⚠️ **The first Controls in this project that take a click.** `InputRouter`
## never marks an event handled, so the buttons see the pointer and the touch;
## while the menu is up the car is parked, so the thumbs the router still reads
## move nothing. `ui_cancel` is read here — a UI action, not a gameplay one —
## for the way back from a page.

## The player picked a mode. `Main` starts the level in it and frees this.
signal started(mode: DayClock.Mode)
## The player picked CONTINUE (`Q253`): `Main` puts `run`, the save HOME
## read, back.
signal continued(run: RunSave)
## The player picked a language; `Locale.language()` already answers it.
signal language_changed(code: String)
## The player picked the steering thumb's response; `ControlOptions.steering()`
## already answers it, and `Main` tells the router.
signal steering_changed
## The player swapped the thumbs' sides: new touch zones and a new HUD, `Main`'s.
signal side_changed
## A page opened; `Main` hands `shot` to the camera round the parked car.
signal page_shown(shot: MenuShot)
## The pause's RESUME: `Main` unpauses the drive where it stood and frees this.
signal resumed
## The pause's RESET CAR (`Q229`): `Main` unpauses and has the level put the
## car back onto the nearest road, the run and its fare going on.
signal reset
## The pause's way out: `Main` parks the level and opens a fresh menu, on a
## free drive's REPORT or on HOME.
signal ended

## Chooses whether the menu is shown at all. `off` for every scripted run.
const MENU_ARG: String = "--menu="
## The page the menu opens on; absent or unknown, the home page.
const PAGE_ARG: String = "--menu-page="
## `on` fills the 成績表 with `SessionTally.sample`, for a frame.
const SAMPLE_ARG: String = "--menu-sample="
## Over the HUD (10), under the dev overlay (127).
const LAYER: int = 20
## The blur behind the menu's text (`Q163`).
const BACKDROP: Shader = preload("res://assets/shaders/backdrop_blur.gdshader")
## Where `_sheet` puts a sheet's column, for the page that fills it.
const SHEET_COLUMN: NodePath = ^"Centre/Pad/Column"
## The scroll a stacked 成績表 stands in (`Q206`), under its sheet's column.
const SCROLL: String = "Scroll"
## The margin between the scroll and the card, clear of the scroll's bar.
const GUTTER: String = "Gutter"

## `PAGE_ARG` names one of these, lower-cased; `driver.gd` validates the same
## list by hand, since a `--script` tool cannot preload a `class_name` script.
enum Page {
	HOME,
	PLAY,
	OPTIONS,
	CREDITS,
	GUIDE,
	NOTICES,
	REPORT,
	PAUSE,
	RECORD,
	SOUND,
	CONTROLS,
	DISPLAY,
	LANGUAGE
}

## OPTIONS' groups in the order listed, each with the key of its name.
const GROUPS: Dictionary[Page, String] = {
	Page.SOUND: "sound",
	Page.CONTROLS: "controls",
	Page.DISPLAY: "display",
	Page.LANGUAGE: "language",
}


## What a run banked, for the REPORT page (`Q162`). Filled by `Main`: at a
## shift's 交更, or when a free drive ends from its PAUSE (the user's ask), which
## reads the time driven where a shift reads its best.
class Report:
	extends RefCounted
	## The run reported, and the one AGAIN starts.
	var mode: DayClock.Mode = DayClock.Mode.SHIFT
	var total_hkd: float = 0.0
	var deliveries: int = 0
	var bails: int = 0
	## The best after this shift, this one included.
	var best_hkd: float = 0.0
	var new_best: bool = false
	## The run's books, for the 成績表 beside the total; its `driven_s` is a
	## free drive's length.
	var tally: SessionTally = SessionTally.new()


## The shift to report, set before this enters the tree; null opens on HOME.
var report: Report = null
## The free drive's books, for the 成績表 on its PAUSE (`Q169`); null on a shift's
## PAUSE, which has only the way on and the way out.
var pause_tally: SessionTally = null
## Whether this is the pause over a running drive, set before this enters the
## tree; it opens on PAUSE and its ways back lead there, not HOME.
var pausing: bool = false
## Whether the paused run is a shift: its way out is END SHIFT, a free drive's
## END DRIVE, which `Main` follows with the drive's REPORT.
var pausing_shift: bool = false
## Whether the 成績表 stacks into one scrolling column (`Q206`): on a touch
## screen, or set before this enters the tree, as `verify_menu` does.
var stacked: bool = false
## Whether this is a phone, which alone is offered a frame cap: read from the
## device, or set before this enters the tree, as `verify_menu` does.
var phone: bool = false

var _profile: MenuProfile = null
var _style: HudStyle = null
var _text: MenuText = null
var _language: String = Locale.DEFAULT
## The 黑體 the menu's running text and tables are set in, the brush for the
## headings and the choices, and its heavier cut for the game's name (`Q218`).
var _font_hei: Font = null
var _font_brush: Font = null
var _font_title: Font = null
## The same two lines in the English menu: a Latin brush (`Q218`).
var _font_brush_en: Font = null
var _font_title_en: Font = null
var _root: Control = null
var _page: Page = Page.HOME
var _pages: Dictionary[int, Control] = {}
## Where the focus lands when a page opens, so a pad or the keys can drive it.
var _first: Dictionary[int, Button] = {}
## OPTIONS' groups on this device, in this menu (`_groups`), read at build.
var _shown_groups: Array[Page] = []
## The run HOME offers to CONTINUE, read as HOME was built; null for none.
var _saved: RunSave = null
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
	if pausing:
		# The one thing that runs over the paused tree.
		process_mode = Node.PROCESS_MODE_ALWAYS
		_page = Page.PAUSE
	elif _page == Page.PAUSE:
		# The flag's pause is `Main`'s to open, over a drive; this boot menu is
		# freed before it shows.
		_page = Page.HOME
	if report != null:
		_page = Page.REPORT
	elif _page == Page.REPORT:
		report = Report.new()
		# `--mode=free` shoots a free drive's report; anything else a shift's.
		if Cmdline.value(DayClock.MODE_ARG).to_lower() == "free":
			report.mode = DayClock.Mode.FREE
		report.best_hkd = Settings.best_shift_hkd()
		var shown: SessionTally = _shown_tally(report.tally)
		report.tally = shown
		report.total_hkd = shown.total_hkd()
		report.deliveries = shown.deliveries
		report.bails = shown.bails
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
	return true


func _build() -> void:
	stacked = stacked or HudLayout.is_touch()
	phone = phone or ControlOptions.caps_frames()
	_root = HudLayout.safe_root(self)
	_load_faces()
	_pages.clear()
	_first.clear()
	_shown_groups = _groups()
	_pages[Page.GUIDE] = _guide()
	_pages[Page.OPTIONS] = _options()
	for group: Page in _shown_groups:
		_pages[group] = _group(group)
	if pausing:
		# The pages a pause reaches, and no more: built on the tap's frame, with
		# the language and the thumbs' sides left out by construction.
		_pages[Page.PAUSE] = _pause()
	else:
		_pages[Page.HOME] = _home()
		_pages[Page.PLAY] = _play()
		_pages[Page.CREDITS] = _credits()
		_pages[Page.NOTICES] = _notices()
		_pages[Page.REPORT] = _report()
		_pages[Page.RECORD] = _record()
	# The HUD's glass (`Q163`): the drive's brackets, so the menu and the drive
	# are one display. Last, over the pages' backdrops, and unshaded — the
	# backdrops shade the text.
	_root.add_child(HeadUpFrame.styled(_style, false))
	# A page this menu did not build — a group this device has nothing for,
	# named by the flag — is the page the menu starts from.
	if not _pages.has(_page):
		_page = _home_page()
	_show(_page)


## The faces the page's language draws with, loaded the first time it is built
## in that language: an English menu never reads the Chinese files, nor a
## Chinese one the Latin brush.
func _load_faces() -> void:
	if _language != Locale.CHINESE:
		if _font_brush_en == null:
			_font_brush_en = StreetPlate.load_font_brush_en("menu")
			_font_title_en = StreetPlate.load_font_brush_en("menu", true)
	elif _font_hei == null:
		_font_hei = StreetPlate.load_font_hei("menu")
		_font_brush = StreetPlate.load_font_brush("menu")
		_font_title = StreetPlate.load_font_brush("menu", true)


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
		Page.OPTIONS, Page.SOUND, Page.CONTROLS, Page.DISPLAY, Page.LANGUAGE:
			return _profile.shot_options
		Page.CREDITS, Page.GUIDE, Page.NOTICES, Page.RECORD:
			return _profile.shot_sheet
		Page.REPORT:
			return _profile.shot_report
	return _profile.shot_home


func _unhandled_input(event: InputEvent) -> void:
	if not event.is_action_pressed(&"ui_cancel"):
		return
	if _page == Page.PAUSE:
		# The key that paused the drive resumes it.
		get_viewport().set_input_as_handled()
		_on_resume()
	elif _page not in [Page.HOME, Page.REPORT]:
		_show(_back_of(_page))
		get_viewport().set_input_as_handled()


## Where a way back lands: HOME, or PAUSE over a paused drive.
func _home_page() -> Page:
	return Page.PAUSE if pausing else Page.HOME


## One step back from `page`: the notices hang off the credits and a group off
## OPTIONS' list, where there is a list.
func _back_of(page: Page) -> Page:
	if page == Page.NOTICES:
		return Page.CREDITS
	if page in _shown_groups and _shown_groups.size() > 1:
		return Page.OPTIONS
	return _home_page()


## OPTIONS' groups for this device and this menu, in `GROUPS`' order.
func _groups() -> Array[Page]:
	var groups: Array[Page] = [Page.SOUND]
	# The thumbs' own: nothing in it for a keyboard or a pad.
	if stacked:
		groups.append(Page.CONTROLS)
	# The hour is the boot menu's and the frame cap a phone's, so a pause at a
	# desk has nothing to show here.
	if phone or not pausing:
		groups.append(Page.DISPLAY)
	if not pausing:
		groups.append(Page.LANGUAGE)
	return groups


## Where the OPTIONS choice leads: the list, or the one group there is.
func _options_page() -> Page:
	return Page.OPTIONS if _shown_groups.size() > 1 else _shown_groups[0]


# ---------------------------------------------------------------- pages ----


## The title and the three choices, a column off the bottom-left corner: the
## car is the picture and the column keeps off it.
func _home() -> Control:
	var column: VBoxContainer = _column("Home")
	# The game's name in the page's language (`Q208`): 香港的士車神 in the brush,
	# Hong Kong Taxi Ace in the theme's face.
	var title: Label = _line("Title", _text.say("title", _language))
	_size(title, _profile.title_size_zh, _profile.title_size, _brush(true))
	# One line, wider than the column: the name is the page's width, not the
	# buttons'.
	title.autowrap_mode = TextServer.AUTOWRAP_OFF
	column.add_child(title)
	# A stroke of the brush under the name, in the taxi's red.
	var swash := InkStroke.new()
	swash.name = "Swash"
	swash.ink = _style.brush_stroke
	swash.seed_value = 7
	swash.custom_minimum_size = Vector2(_profile.button_px.x, _profile.button_gap_px * 1.5)
	swash.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	column.add_child(swash)
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
	_saved = _saved_run()
	if _saved == null:
		column.add_child(_gap("Gap", _profile.button_gap_px * 2))
		_first[Page.HOME] = _button(column, "Play", "start", _show.bind(Page.PLAY))
	else:
		_saved_choices(column, _saved)
	_button(column, "Record", "record", _show.bind(Page.RECORD))
	_button(column, "Guide", "guide", _show.bind(Page.GUIDE))
	_button(column, "Options", "options", _show.bind(_options_page()))
	_button(column, "Credits", "credits", _show.bind(Page.CREDITS))
	return column


## A saved run's CONTINUE (`Q253`), focused, beside PLAY in PLAY's row — two
## half-width choices — with the run's line tight under them. The column grows
## from the bottom and a handset has no height to spare over the title, so
## the line stands in for half of the gap above the choices and HOME is
## barely taller than without a save.
func _saved_choices(column: VBoxContainer, saved: RunSave) -> void:
	column.add_child(_gap("Gap", _profile.button_gap_px))
	var block := VBoxContainer.new()
	block.name = "Saved"
	block.add_theme_constant_override(&"separation", 0)
	column.add_child(block)
	var row := HBoxContainer.new()
	row.name = "Choices"
	row.add_theme_constant_override(&"separation", _profile.button_gap_px)
	block.add_child(row)
	_first[Page.HOME] = _button(row, "Continue", "continue", _on_continue)
	_button(row, "Play", "start", _show.bind(Page.PLAY))
	var half := Vector2((_profile.button_px.x - _profile.button_gap_px) / 2.0, _profile.button_px.y)
	for panel: Node in row.get_children():
		(panel as Control).custom_minimum_size = half
	var caption: Label = _line("Caption", _saved_caption(saved))
	_size(caption, _profile.body_size_zh, _profile.body_size)
	caption.add_theme_color_override(&"font_color", _style.chip_muted)
	block.add_child(caption)


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


## OPTIONS: its groups, a choice each, and the way back (`Q223`).
func _options() -> Control:
	var column: VBoxContainer = _column("Options")
	_heading(column, "Heading", _text.say("options", _language))
	for group: Page in _shown_groups:
		var choice: Button = _button(column, _group_name(group), GROUPS[group], _show.bind(group))
		if not _first.has(Page.OPTIONS):
			_first[Page.OPTIONS] = choice
	column.add_child(_gap("Gap", _profile.button_gap_px))
	_button(column, "Back", "back", _show.bind(_home_page()))
	return column


## A group's node name: "Sound" for `Page.SOUND`.
func _group_name(group: Page) -> String:
	return str(Page.find_key(group)).capitalize()


## One of OPTIONS' groups: its name, its options — each a row of choices with
## the current one marked — and the way back.
func _group(group: Page) -> Control:
	var column: VBoxContainer = _column(_group_name(group))
	_heading(column, "Heading", _text.say(GROUPS[group], _language))
	match group:
		Page.SOUND:
			_sound(column)
		Page.CONTROLS:
			_controls(column)
		Page.DISPLAY:
			_display(column)
		Page.LANGUAGE:
			_languages(column)
	column.add_child(_gap("Gap", _profile.button_gap_px))
	_button(column, "Back", "back", _show.bind(_back_of(group)))
	# The focus lands on the first choice that is one: a current choice is a
	# marker, and BACK is always there to take it.
	for found: Node in column.find_children("Button", "Button", true, false):
		if not (found as Button).disabled:
			_first[group] = found as Button
			break
	return column


## An option under `column`: a row named `node_name` of choices side by side,
## the one at `current` marked, under the heading `heading_key` names — none
## for "", where the page's own heading says it. Each of `choices` is a node
## name, a text key and what a press does.
func _choices(
	column: VBoxContainer, node_name: String, heading_key: String, choices: Array, current: int
) -> void:
	if not heading_key.is_empty():
		if column.get_child_count() > 1:
			column.add_child(_gap(node_name + "Gap", _profile.button_gap_px))
		var heading: Label = _line(node_name + "Heading", _text.say(heading_key, _language))
		_size(heading, _profile.heading_size_zh, _profile.heading_size, _brush())
		column.add_child(heading)
	var row := HBoxContainer.new()
	row.name = node_name
	row.add_theme_constant_override(&"separation", _profile.button_gap_px)
	column.add_child(row)
	for index: int in choices.size():
		var choice: Array = choices[index]
		# The current one is the marker: lit and not a choice, so there is
		# nothing to press that changes nothing.
		_mark_current(_button(row, choice[0], choice[1], choice[2]), index == current)


## The language: the two, the current one marked.
func _languages(column: VBoxContainer) -> void:
	_choices(
		column,
		"Languages",
		"",
		[
			["Chinese", "language_zh", _pick.bind(Locale.CHINESE)],
			["English", "language_en", _pick.bind(Locale.ENGLISH)],
		],
		0 if _language == Locale.CHINESE else 1
	)


## What is drawn: a phone's frame cap (`Q223`), and the hour (`Q160`) —
## whether the day runs to night as game time passes in free mode; a shift
## always runs it (`Q162`), and a drive under way keeps the hour it has.
func _display(column: VBoxContainer) -> void:
	if phone:
		var offered: PackedInt32Array = ControlOptions.frame_caps()
		var caps: Array = []
		for fps: int in offered:
			caps.append(["Fps%d" % fps, "frame_%d" % fps, _pick_frame_cap.bind(fps)])
		_choices(column, "FrameCaps", "frame_rate", caps, offered.find(ControlOptions.frame_cap()))
	if not pausing:
		_choices(
			column,
			"Times",
			"time",
			[
				["Cycle", "time_cycle", _pick_time.bind(true)],
				["Day", "time_day", _pick_time.bind(false)],
			],
			0 if Settings.day_cycle() else 1
		)


## The thumbs (`Q223`): how sharply the steering one answers, whether their
## controls follow them or stand still (`Q239`), and — on the boot menu alone,
## since it is a new HUD — which side the steering one is on.
func _controls(column: VBoxContainer) -> void:
	var steerings: Array = []
	for steering: String in ControlOptions.STEERINGS:
		steerings.append(
			[steering.capitalize(), "steering_" + steering, _pick_steering.bind(steering)]
		)
	_choices(
		column,
		"Steerings",
		"steering",
		steerings,
		ControlOptions.STEERINGS.find(ControlOptions.steering())
	)
	# Where the controls stand (`Q239`). The pause offers it too: the sticks
	# draw where the router says a thumb's control is, so it needs no new HUD.
	_choices(
		column,
		"Anchors",
		"anchor",
		[
			["Relative", "anchor_relative", _pick_anchor.bind(ControlOptions.RELATIVE)],
			["Fixed", "anchor_fixed", _pick_anchor.bind(ControlOptions.FIXED)],
		],
		ControlOptions.ANCHORS.find(ControlOptions.anchor())
	)
	# Spun or slid, whichever way the controls stand (`Q251`); the pause's too.
	_choices(
		column,
		"Wheels",
		"wheel",
		[
			["Spin", "wheel_spin", _pick_wheel.bind(ControlOptions.SPIN)],
			["Slide", "wheel_slide", _pick_wheel.bind(ControlOptions.SLIDE)],
		],
		ControlOptions.WHEELS.find(ControlOptions.wheel())
	)
	if not pausing:
		_choices(
			column,
			"Sides",
			"side",
			[
				["Left", "side_left", _pick_side.bind(false)],
				["Right", "side_right", _pick_side.bind(true)],
			],
			1 if ControlOptions.steer_on_right() else 0
		)


## The sound (`Q221`): on or off, and how loud — the Master bus, so every voice
## follows. Then the driving music's own switch and level under it (`Q246`).
func _sound(column: VBoxContainer) -> void:
	_choices(
		column,
		"Sounds",
		"",
		[
			["On", "sound_on", _pick_switch.bind(true, Settings.sound_on, Settings.set_sound_on)],
			[
				"Off",
				"sound_off",
				_pick_switch.bind(false, Settings.sound_on, Settings.set_sound_on)
			],
		],
		0 if Settings.sound_on() else 1
	)
	_volume(column, "Volume", Settings.volume(), Settings.set_volume)
	_choices(
		column,
		"Music",
		"music",
		[
			["On", "sound_on", _pick_switch.bind(true, Settings.music_on, Settings.set_music_on)],
			[
				"Off",
				"sound_off",
				_pick_switch.bind(false, Settings.music_on, Settings.set_music_on)
			],
		],
		0 if Settings.music_on() else 1
	)
	_volume(column, "MusicVolume", Settings.music_volume(), Settings.set_music_volume)


## Save the steering thumb's response and say so; the page is redrawn so the
## marker moves. Through `ControlOptions`, not the pick: a flag pins it.
func _pick_steering(choice: String) -> void:
	Settings.set_steering(choice)
	if ControlOptions.steering() != choice:
		push_warning("menu: --touch-steer= pins the steering this run; the choice is saved")
		return
	steering_changed.emit()
	_relabel.call_deferred()


## Save where the thumbs' controls stand and say so, as the response is said:
## the router reads both on the one signal.
func _pick_anchor(choice: String) -> void:
	Settings.set_anchor(choice)
	if ControlOptions.anchor() != choice:
		push_warning("menu: --touch-anchor= pins the controls this run; the choice is saved")
		return
	steering_changed.emit()
	_relabel.call_deferred()


## Save how the wheel is turned and say so, as the anchor is said.
func _pick_wheel(choice: String) -> void:
	Settings.set_wheel(choice)
	if ControlOptions.wheel() != choice:
		push_warning("menu: --touch-wheel= pins the wheel this run; the choice is saved")
		return
	steering_changed.emit()
	_relabel.call_deferred()


## Save the steering thumb's side and say so: `Main` builds the zones and the
## HUD afresh.
func _pick_side(on_right: bool) -> void:
	Settings.set_steer_on_right(on_right)
	if ControlOptions.steer_on_right() != on_right:
		push_warning("menu: --touch-side= pins the thumbs' sides this run; the choice is saved")
		return
	side_changed.emit()
	_relabel.call_deferred()


## Save a phone's frame cap and set it at once.
func _pick_frame_cap(fps: int) -> void:
	if fps == ControlOptions.frame_cap():
		return
	Settings.set_frame_cap(fps)
	ControlOptions.apply_frame_cap()
	_relabel.call_deferred()


## Save the hour's mode and redraw the page so the marker moves. `DayClock`
## reads the saved option when the car first drives off.
func _pick_time(cycle: bool) -> void:
	if cycle == Settings.day_cycle():
		return
	Settings.set_day_cycle(cycle)
	if not Cmdline.value(DayClock.CYCLE_ARG).is_empty():
		push_warning("menu: --day-cycle= pins the hour this run; the choice is saved for the next")
	_relabel.call_deferred()


## A switch of the sound's or the music's: `save` it where it differs from
## `saved`, set the buses and redraw the page so the marker moves.
func _pick_switch(on: bool, saved: Callable, save: Callable) -> void:
	if on == saved.call():
		return
	save.call(on)
	Settings.apply_sound()
	_relabel.call_deferred()


## How loud, under `column`: the level `at` named in a line called `node_name`
## over a slider a choice's size (`node_name` + "Slider"), so a thumb takes it,
## and `save` handed where it went. The track is the muted ink, what is filled
## the dial's amber like a current choice, and the lighter ink under the
## pointer or the focus, where left and right move it a notch.
func _volume(column: VBoxContainer, node_name: String, at: float, save: Callable) -> void:
	var level: Label = _note(column, node_name, _volume_text(at), _style.chip_muted)
	var slider := HSlider.new()
	slider.name = node_name + "Slider"
	slider.min_value = 0.0
	slider.max_value = 1.0
	slider.step = _profile.volume_step
	slider.value = at
	slider.custom_minimum_size = _profile.button_px
	slider.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	slider.add_theme_stylebox_override(&"slider", _track(_style.chip_muted))
	slider.add_theme_stylebox_override(&"grabber_area", _track(_style.dial_needle))
	slider.add_theme_stylebox_override(&"grabber_area_highlight", _track(_style.chip_ink))
	# Hover IS focus, as on a choice.
	slider.mouse_entered.connect(slider.grab_focus)
	slider.value_changed.connect(_on_volume.bind(save, level))
	column.add_child(slider)


## A length of the slider's track in `ink`.
func _track(ink: Color) -> StyleBoxFlat:
	var track := StyleBoxFlat.new()
	track.bg_color = ink
	track.content_margin_top = _profile.volume_track_px / 2.0
	track.content_margin_bottom = _profile.volume_track_px / 2.0
	return track


## The slider moved: saved and heard at once, and the line over it renamed. No
## rebuild — the slider under the thumb is under the root a rebuild frees.
func _on_volume(value: float, save: Callable, level: Label) -> void:
	save.call(value)
	Settings.apply_sound()
	level.text = _volume_text(value)


func _volume_text(level: float) -> String:
	return _text.say("volume", _language) % roundi(level * 100.0)


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
		_size(title, _profile.heading_size_zh, _profile.heading_size, _brush())
		step.add_child(title)
		var body: Label = _line(
			"Body", MenuText.pick((entry as Dictionary).get("body"), _language, "")
		)
		_size(body, _profile.body_size_zh, _profile.body_size)
		body.add_theme_color_override(&"font_color", _style.chip_muted)
		step.add_child(body)

	_first[Page.GUIDE] = _foot(column, _home_page())
	return panel


## 交更 (`Q162`): what the shift banked, over the best, and the way to the
## next — a column off the corner like HOME's, so the car stays the picture.
## A free drive's has its name for a heading and the time driven for the best:
## a drive with no end has no total to weigh.
func _report() -> Control:
	var column: VBoxContainer = _column("Report")
	var shown: Report = report if report != null else Report.new()
	var free: bool = shown.mode == DayClock.Mode.FREE
	var heading: Label = _line("Heading", _text.say("free" if free else "handover", _language))
	_size(heading, _profile.heading_size_zh, _profile.heading_size, _brush())
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
	var best: Label
	if free:
		best = _line("Driven", _text.say("driven", _language) % duration_text(shown.tally.driven_s))
	else:
		best = _line(
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
	_first[Page.REPORT] = _button(
		column, "Again", "again_free" if free else "again", _on_start.bind(shown.mode)
	)
	_button(column, "Menu", "menu", _show.bind(Page.HOME))
	# Only a real report: every other menu builds this page and never shows it.
	if report != null:
		_save_button(column, _beside(column, report.tally))
	return column


## The drive held (the user's ask): a column off the corner like HOME's over
## the frozen frame — the way on, how to play, the options a held drive can
## take (`_groups`), and the way out of the run, a
## shift's END SHIFT recording no best, since half a shift is not a total, and
## a free drive's END DRIVE leading to its REPORT.
func _pause() -> Control:
	var column: VBoxContainer = _column("Pause")
	_heading(column, "Heading", _text.say("paused", _language))
	_first[Page.PAUSE] = _button(column, "Resume", "resume", _on_resume)
	_button(column, "Reset", "reset_car", _on_reset)
	_button(column, "Guide", "guide", _show.bind(Page.GUIDE))
	_button(column, "Options", "options", _show.bind(_options_page()))
	if pause_tally != null:
		_save_button(column, _beside(column, pause_tally))
	column.add_child(_gap("Gap", _profile.button_gap_px))
	_button(column, "End", "end_shift" if pausing_shift else "end_drive", _on_end)
	return column


## The lifetime record (`P3-76`, `Q169`), off HOME: the 成績表's form on every run
## added up, over the shifts and the fares.
func _record() -> Control:
	var panel: ChamferPanel = _sheet(
		"Record", _profile.ledger_px, _profile.ledger_stacked_width_px if stacked else 0
	)
	var column: VBoxContainer = panel.get_node(SHEET_COLUMN)
	# The page's name and the best shift on one line, the best on the right
	# where the sheet's money stands, and the runs under them: three lines of
	# one size took a third of a phone's glass before the first table.
	var top := HBoxContainer.new()
	top.name = "Top"
	column.add_child(top)
	_sheet_type(_heading(top, "Heading", _text.say("record", _language)))
	var best: Label = _note(
		top,
		"Best",
		_text.say("best", _language) + FareFace.money(Settings.best_shift_hkd()),
		_style.plate_ink
	)
	best.size_flags_horizontal = Control.SIZE_SHRINK_END
	best.size_flags_vertical = Control.SIZE_SHRINK_END
	best.autowrap_mode = TextServer.AUTOWRAP_OFF
	_sheet_type(best)
	var tally: SessionTally = _shown_tally(Settings.lifetime())
	_sheet_type(
		_note(
			column,
			"Runs",
			(
				_text.say("record_runs", _language)
				% [Settings.shifts_finished(), tally.deliveries, tally.bails]
			),
			_style.chip_muted
		)
	)
	_scrolled(column, _ledger(tally))
	var foot: HBoxContainer = _foot_row(column)
	_save_button(foot, column)
	_first[Page.RECORD] = _button(foot, "Back", "back", _show.bind(Page.HOME))
	return panel


## The 成績表 under a page's column, off the safe area's right edge on its own
## blurred ground, shown and hidden with `page`. Returns the sheet's column.
func _beside(page: Control, tally: SessionTally) -> VBoxContainer:
	var panel: ChamferPanel = _panel("Ledger")
	if stacked:
		# What the page's column leaves, top to foot (`Q206`): never over it.
		panel.set_anchors_preset(Control.PRESET_FULL_RECT)
		panel.offset_left = _profile.margin_px.x * 1.5 + _profile.button_px.x
		panel.offset_right = -_profile.margin_px.x / 2.0
		panel.offset_top = _profile.margin_px.y / 2.0
		panel.offset_bottom = -_profile.margin_px.y / 2.0
	else:
		panel.set_anchors_preset(Control.PRESET_CENTER_RIGHT)
		panel.offset_left = -_profile.margin_px.x / 2.0 - _profile.ledger_px.x
		panel.offset_right = -_profile.margin_px.x / 2.0
		panel.offset_top = -_profile.ledger_px.y / 2.0
		panel.offset_bottom = _profile.ledger_px.y / 2.0
	_root.add_child(panel)
	_backdrop(panel, 1.0).set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var pad: MarginContainer = padded(_profile.credits_pad_px)
	pad.set_anchors_preset(Control.PRESET_FULL_RECT)
	panel.add_child(pad)
	var column := VBoxContainer.new()
	column.name = "Column"
	column.add_theme_constant_override(&"separation", _profile.button_gap_px)
	pad.add_child(column)
	_sheet_type(_heading(column, "Heading", _text.say("sheet_title", _language)))
	_scrolled(column, _ledger(_shown_tally(tally)))
	# A lambda, not `_follow.bind`: the column's backdrop already holds that
	# connection, and two binds of one method are one connection to Godot.
	page.visibility_changed.connect(func() -> void: panel.visible = page.visible)
	return column


## SAVE RESULT under `parent`, for `sheet`'s column (`SheetImage`, `P3-80`); none
## on a phone.
func _save_button(parent: Control, sheet: Control) -> void:
	if not SheetImage.offered():
		return
	var button: Button = _button(parent, "Save", "sheet_save")
	button.pressed.connect(_save_sheet.bind(sheet, button))


## The press: the sheet drawn and saved, and the button saying which. The
## focus goes back where it was: disabling the button dropped it.
func _save_sheet(sheet: Control, button: Button) -> void:
	var focused: bool = button.has_focus()
	button.disabled = true
	var image: Image = await SheetImage.shoot(self, sheet, _profile, _style)
	# The two frames it waited are enough for AGAIN or RESUME to take the menu.
	if not is_instance_valid(button):
		return
	var saved: bool = not SheetImage.save(image).is_empty()
	button.text = _text.say("sheet_saved" if saved else "sheet_save_failed", _language)
	button.disabled = false
	if focused:
		button.grab_focus()


func _ledger(tally: SessionTally) -> LedgerCard:
	var card := LedgerCard.new()
	card.name = "Card"
	card.build(tally, _text, _profile, _style, _language, _font_hei, stacked)
	return card


## `card` under `column`: as it is at a desk, or stacked in a scroll that takes
## the column's slack on a phone, so the page's buttons stay on the glass.
func _scrolled(column: VBoxContainer, card: LedgerCard) -> void:
	if not stacked:
		column.add_child(card)
		return
	var scroll := ScrollContainer.new()
	scroll.name = SCROLL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	# The bar draws over the scroll's child, so the card stands clear of it:
	# its last column of digits was under the bar.
	var gutter := MarginContainer.new()
	gutter.name = GUTTER
	gutter.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	gutter.add_theme_constant_override(
		&"margin_right",
		ceili(scroll.get_v_scroll_bar().get_combined_minimum_size().x) + _profile.button_gap_px
	)
	gutter.add_child(card)
	scroll.add_child(gutter)
	column.add_child(scroll)


## A sheet's own line at the stacked 成績表's scale, so a heading over the
## tables is never smaller than the rows under it (`Q206`).
func _sheet_type(label: Label) -> void:
	var px: int = label.get_theme_font_size(&"font_size")
	label.add_theme_font_size_override(&"font_size", _profile.ledger_scaled(px, stacked))


## `seconds` on a stopwatch, to the second begun: "4:05" under the hour,
## "1:02:09" over it.
static func duration_text(seconds: float) -> String:
	var whole: int = floori(maxf(seconds, 0.0))
	var hours: int = floori(whole / 3600.0)
	var minutes: int = floori(whole / 60.0) % 60
	if hours > 0:
		return "%d:%02d:%02d" % [hours, minutes, whole % 60]
	return "%d:%02d" % [minutes, whole % 60]


## The run CONTINUE picks up: the saved one, or a sample under `SAMPLE_ARG`,
## and none under any other frame's flag — a frame never shows what this
## machine last drove.
func _saved_run() -> RunSave:
	if Cmdline.value(SAMPLE_ARG) == "on":
		return RunSave.sample()
	if not Cmdline.value(PAGE_ARG).is_empty():
		return null
	return RunSave.load_saved()


## CONTINUE's line: the mode, the shift's hour or the time a free drive has
## run, and what the run has banked.
func _saved_caption(saved: RunSave) -> String:
	var shift: bool = saved.mode == DayClock.Mode.SHIFT
	var when: String = (
		DayClock.clock_text(saved.hour_h)
		if shift and not is_nan(saved.hour_h)
		else duration_text(saved.driven_s())
	)
	return (
		_text.say("saved_run", _language)
		% [
			_text.say("shift" if shift else "free", _language),
			when,
			FareFace.money(saved.earned_hkd())
		]
	)


## What a 成績表 shows: `tally`, or a filled sheet under `SAMPLE_ARG`.
func _shown_tally(tally: SessionTally) -> SessionTally:
	return SessionTally.sample() if Cmdline.value(SAMPLE_ARG) == "on" else tally


# -------------------------------------------------------------- actions ----


func _on_start(mode: DayClock.Mode) -> void:
	_leave()
	started.emit(mode)


func _on_continue() -> void:
	_leave()
	continued.emit(_saved)


func _on_resume() -> void:
	_leave()
	resumed.emit()


func _on_reset() -> void:
	_leave()
	reset.emit()


func _on_end() -> void:
	_leave()
	ended.emit()


## Off the screen, deaf and freed, before the signal that hands the run back.
func _leave() -> void:
	# Released first: a `ui_accept` still held would land on whatever took the
	# focus next, and Space is also the handbrake.
	get_viewport().gui_release_focus()
	set_process_unhandled_input(false)
	visible = false
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
	HudLayout.bleed(backdrop, _root)
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
## With `full_height_width_px` the padded column is that wide and runs top to
## foot of the safe area instead (`Q206`), for a sheet whose middle scrolls.
func _sheet(node_name: String, size_px: Vector2, full_height_width_px: int = 0) -> ChamferPanel:
	var full_height: bool = full_height_width_px > 0
	var panel: ChamferPanel = _panel(node_name)
	panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(panel)
	var shade: ColorRect = _backdrop(panel, 1.0)
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	# To the glass, past the notch's line (`Q204`); the text stays inside it.
	HudLayout.bleed(shade, _root)

	var centre: Control = Control.new() if full_height else CenterContainer.new()
	centre.name = "Centre"
	centre.set_anchors_preset(Control.PRESET_FULL_RECT)
	panel.add_child(centre)

	var pad: MarginContainer = padded(_profile.credits_pad_px)
	if full_height:
		pad.set_anchors_preset(Control.PRESET_CENTER_TOP)
		pad.anchor_bottom = 1.0
		pad.offset_left = -full_height_width_px / 2.0
		pad.offset_right = full_height_width_px / 2.0
	else:
		pad.custom_minimum_size = size_px
	centre.add_child(pad)

	var column := VBoxContainer.new()
	column.name = "Column"
	column.add_theme_constant_override(&"separation", _profile.button_gap_px)
	pad.add_child(column)
	return panel


## A sheet's padding, `px` on every side: the panels', and `SheetImage`'s.
static func padded(px: int) -> MarginContainer:
	var pad := MarginContainer.new()
	pad.name = "Pad"
	for side: StringName in [&"margin_left", &"margin_top", &"margin_right", &"margin_bottom"]:
		pad.add_theme_constant_override(side, px)
	return pad


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
	foot.name = SheetImage.FOOT
	foot.alignment = BoxContainer.ALIGNMENT_END
	foot.add_theme_constant_override(&"separation", _profile.button_gap_px)
	column.add_child(foot)
	return foot


## A choice: bare brush lettering (`Q163`, `Q218`), with a stroke of the brush
## behind the words while the pointer or the focus is on it. Returned for the
## focus and the marker; the panel goes under `parent`.
func _button(
	parent: Control, node_name: String, key: String, pressed: Callable = Callable()
) -> Button:
	var panel: ChamferPanel = _panel(node_name)
	panel.custom_minimum_size = _profile.button_px
	# Its own width in any container: a lone BACK under a row of two would
	# otherwise stretch to the row.
	panel.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	parent.add_child(panel)
	# The highlight: a stroke of the brush behind the words, unseen until the
	# pointer or the focus is on the choice. Each choice its own hand.
	var stroke := InkStroke.new()
	stroke.name = "Stroke"
	stroke.ink = Color.TRANSPARENT
	stroke.seed_value = key.hash()
	stroke.set_anchors_preset(Control.PRESET_FULL_RECT)
	stroke.offset_left = -_style.plate_pad.y
	stroke.offset_top = _style.plate_pad.y / 2.0
	stroke.offset_bottom = -_style.plate_pad.y / 2.0
	panel.add_child(stroke)

	var button := Button.new()
	button.name = "Button"
	button.flat = true
	button.text = _text.say(key, _language)
	button.set_anchors_preset(Control.PRESET_FULL_RECT)
	button.focus_mode = Control.FOCUS_ALL
	button.alignment = HORIZONTAL_ALIGNMENT_LEFT
	# The stroke is the whole look; the theme's box would draw over it.
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
		button.add_theme_color_override(state, _style.chip_ink)
	_size(button, _profile.button_size_zh, _profile.button_size, _brush())
	if pressed.is_valid():
		button.pressed.connect(pressed)
	# Hover IS focus, so the stroke follows the pointer and the pad alike
	# and there is one highlighted choice at a time.
	button.mouse_entered.connect(button.grab_focus)
	button.focus_entered.connect(_light.bind(stroke, true))
	button.focus_exited.connect(_light.bind(stroke, false))
	panel.add_child(button)
	return button


func _light(stroke: InkStroke, lit: bool) -> void:
	stroke.ink = _style.brush_stroke if lit else Color.TRANSPARENT


## The current option: lit in the dial's amber — not the accent, which is the
## focus's and would make the current choice and the cursor one colour — and
## not a button any more.
func _mark_current(button: Button, current: bool) -> void:
	if not current:
		return
	button.disabled = true
	button.focus_mode = Control.FOCUS_NONE
	button.add_theme_color_override(&"font_disabled_color", _style.dial_needle)


## A sheet's heading under `parent`: a line in the dial's amber at the heading
## size.
func _heading(parent: Control, node_name: String, text: String) -> Label:
	var heading: Label = _line(node_name, text)
	_size(heading, _profile.heading_size_zh, _profile.heading_size, _brush())
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


## A line of body text under `parent`, in `ink`.
func _note(parent: Control, node_name: String, said: String, ink: Color) -> Label:
	var note: Label = _line(node_name, said)
	_size(note, _profile.body_size_zh, _profile.body_size)
	note.add_theme_color_override(&"font_color", ink)
	parent.add_child(note)
	return note


func _gap(node_name: String, px: int) -> Control:
	var gap := Control.new()
	gap.name = node_name
	gap.mouse_filter = Control.MOUSE_FILTER_IGNORE
	gap.custom_minimum_size = Vector2(0.0, px)
	return gap


## The brush for the page's language, the heavier cut for the game's name.
func _brush(title: bool = false) -> Font:
	if _language == Locale.CHINESE:
		return _font_title if title else _font_brush
	return _font_title_en if title else _font_brush_en


## A size for the language: a Chinese face sets larger than the Latin at every
## line. The line takes `face`; with none, Chinese takes the 黑體 — the menu's
## running text is interface, and the Kai is the HUD's, for names (`Q218`) —
## and English the theme's.
func _size(control: Control, zh: int, en: int, face: Font = null) -> void:
	var chinese: bool = _language == Locale.CHINESE
	control.add_theme_font_size_override(&"font_size", Locale.pick(zh, en, _language))
	var font: Font = face
	if font == null and chinese:
		font = _font_hei
	if font != null:
		control.add_theme_font_override(&"font", font)
