extends Node
## The entry point (`P5-24`): the one node that holds both `World` and `GUI`,
## and therefore the one that may hand the HUD its car.
##
## The guide's rule is that siblings know only their own hierarchies and an
## ancestor mediates; before this the HUD found the first car in a group,
## which crossed the World / GUI boundary from below. A level change swaps
## `World`'s child and hands the next car in here — nothing under `GUI`
## searches for one.
##
## The start menu (`P6-1`) is mediated here for the same reason: it sits under
## `GUI`, the level it holds still sits under `World`, and this is the one node
## that may tell the level to park while the menu is up and to go on `started`.
##
## And the shift's end (`Q162`): on the level's `shift_over` the level parks,
## the best is recorded and a fresh menu opens on the report, whose AGAIN is a
## `started` like the first — the level restarts in place, never reloads.
##
## And the pause (`Q165`, the user's ask): Esc, the HUD's button or the app
## losing the screen pause the TREE — not `DriveHarness.park`, which stands the
## car in the showroom — so the car, the fare's clock, the shift's hour and
## the parked roster hold where they are. A fresh menu on PAUSE runs alone over
## it. RESUME unpauses; the way out parks the level and opens HOME, writing no
## best: half a shift is not a total, though what it did joins the lifetime
## record, saved as the pause opens. A free drive's way out opens its REPORT
## instead (`Q189`): what it banked and how long it drove. This node stays
## pausable — its children would inherit anything else — so the menu's signals
## are what reach it while the tree is held.

## How long `--menu-page=pause` drives before it pauses: the chase rig is
## snapped onto the car at start and needs a moment to frame it.
const PAUSE_PAGE_AFTER_S: float = 1.0

## The level in play. Assign in the scene.
@export var level: DriveHarness
## The player's HUD. Assign in the scene.
@export var hud: Hud
## The start menu. Assign in the scene; a scene without one, or a run under
## `--menu=off`, boots straight into the drive as it always did.
@export var menu: StartMenu

## Where a menu opened after the first one goes: the first one's parent.
var _gui: Node = null
## Whether a run has ended, so the next start needs a fresh HUD.
var _ended: bool = false
## The menu over a paused drive, while one is up.
var _pause_menu: StartMenu = null


func _ready() -> void:
	# After `World` and `GUI` have readied: children ready first, so the level
	# has placed its car and the HUD has built its plate before this runs.
	if hud == null:
		push_warning("Main has no HUD assigned; the plate and the speed will not draw.")
	if level == null:
		push_warning("Main has no level assigned; the HUD has no car to read.")
		return
	# Under `--menu=off` the menu frees itself in its own `_ready`, which is
	# deferred to the end of this frame, so the export still points at a node
	# that is leaving: its own queued state is the one answer, not a second
	# read of the flag.
	var menu_up: bool = menu != null and not menu.is_queued_for_deletion()
	if menu_up:
		_gui = menu.get_parent()
	_hand_over()
	level.shift_over.connect(_on_shift_over)
	if not menu_up:
		return
	if Cmdline.value(StartMenu.PAGE_ARG).to_lower() == "pause":
		# A frame of the pause is one `drive.sh` run: the drive starts as
		# PLAY would start it and is held once the chase rig has settled.
		menu.queue_free()
		_on_started(DayClock.mode_from_flag())
		# On physics time: the boot's load stalls the wall clock past a second.
		get_tree().create_timer(PAUSE_PAGE_AFTER_S, false, true).timeout.connect(pause)
		return
	level.park()
	if is_instance_valid(hud):
		hud.visible = false
	_follow_menu(menu)
	_cover_boot(menu)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed(&"ui_cancel") and _can_pause():
		get_viewport().set_input_as_handled()
		pause()


## The app losing the screen holds the run: a call or a notification must not
## spend a shift. Delivered whether or not the tree is paused, and ignored
## where there is nothing to hold.
func _notification(what: int) -> void:
	match what:
		NOTIFICATION_APPLICATION_PAUSED, NOTIFICATION_APPLICATION_FOCUS_OUT:
			pause()
		NOTIFICATION_WM_CLOSE_REQUEST:
			_bank_tally(false)


## Only a drive in play pauses: never under `--menu=off` (every scripted run),
## over a menu, or twice.
func _can_pause() -> bool:
	return (
		_gui != null
		and _pause_menu == null
		and level != null
		and level.vehicle != null
		and not level.vehicle.parked
		and not get_tree().paused
	)


## Hold the drive where it stands and put the pause over it.
func pause() -> void:
	if not _can_pause():
		return
	get_tree().paused = true
	# Before anything can end the app: this is also the way out of a run, and
	# nothing moves while the tree is held, so END needs no second save.
	_bank_tally(false)
	var shown := StartMenu.new()
	shown.name = "PauseMenu"
	shown.pausing = true
	shown.pausing_shift = _in_shift()
	if not shown.pausing_shift and is_instance_valid(level.fares):
		shown.pause_tally = level.fares.tally
	shown.resumed.connect(_release_pause)
	shown.ended.connect(_on_run_ended)
	_gui.add_child(shown)
	_pause_menu = shown


## RESUME, and the first half of the way out: the pause menu has freed itself
## and the tree runs again.
func _release_pause() -> void:
	_pause_menu = null
	get_tree().paused = false


## Out of a paused run: the level parks under a fresh HOME as at boot, or a
## free drive's REPORT, and the next PLAY starts clean through
## `DriveHarness.play`. Read before the park: nothing resets the books but
## `play`, and the tally was banked as the pause opened.
func _on_run_ended() -> void:
	var report: StartMenu.Report = _free_report()
	_release_pause()
	level.park()
	_ended = true
	if is_instance_valid(hud):
		hud.visible = false
	_open_menu(report)


## A free drive's books for its REPORT, or null for a shift ended early, which
## goes HOME: half a shift is not a total.
func _free_report() -> StartMenu.Report:
	if _in_shift():
		return null
	var report: StartMenu.Report = _report_of_run()
	report.mode = DayClock.Mode.FREE
	return report


func _in_shift() -> bool:
	return level.clock != null and level.clock.mode == DayClock.Mode.SHIFT


## The run's books in a REPORT: blank under `--fares=off`, which frees the loop.
func _report_of_run() -> StartMenu.Report:
	var report := StartMenu.Report.new()
	if is_instance_valid(level.fares):
		report.tally = level.fares.tally
		report.total_hkd = level.fares.earned_hkd
		report.deliveries = level.fares.deliveries
		report.bails = level.fares.bails
	return report


## The boot's shaders compiled under a cover (`ShaderWarmup`): the menu takes
## no input until it lifts, so a key cannot start a drive the cover hides.
func _cover_boot(shown: StartMenu) -> void:
	var cover := ShaderWarmup.new()
	cover.name = "BootCover"
	_gui.add_child(cover)
	shown.process_mode = Node.PROCESS_MODE_DISABLED
	cover.finished.connect(_uncover.bind(shown))
	cover.warm(level, level.regions, hud if is_instance_valid(hud) else null)


func _uncover(shown: StartMenu) -> void:
	if is_instance_valid(shown):
		shown.process_mode = Node.PROCESS_MODE_INHERIT


func _follow_menu(shown: StartMenu) -> void:
	shown.started.connect(_on_started)
	shown.language_changed.connect(_on_language_changed)
	shown.page_shown.connect(level.frame_menu)
	# The page it opened on was shown before anything listened; cut to it.
	level.frame_menu(shown.shot(), true)


## The HUD reads the level's car and fare loop. Guarded for `--hud=off`, where
## the HUD has freed itself before this runs.
func _hand_over() -> void:
	if not is_instance_valid(hud):
		return
	hud.vehicle = level.vehicle
	hud.fares = level.fares
	hud.clock = level.clock
	hud.pause_pressed.connect(pause)
	# No menu, no pause: the button would take a tap and do nothing.
	hud.pausable = _gui != null


func _on_started(mode: DayClock.Mode) -> void:
	if _ended:
		# The last run's receipt and total are still on its face.
		_ended = false
		_renew_hud()
	level.play(mode)
	if is_instance_valid(hud):
		hud.visible = true


## 交更 (`Q162`): the level parks under the report, and the run's total is
## weighed against the best. A run with no menu — every scripted one — says
## the total on the log, parks, and writes no record: the best is a player's.
func _on_shift_over() -> void:
	var report: StartMenu.Report = _report_of_run()
	print(
		(
			"shift over: HK$%.1f, %d delivered, %d walked"
			% [report.total_hkd, report.deliveries, report.bails]
		)
	)
	level.park()
	_ended = true
	if is_instance_valid(hud):
		hud.visible = false
	if _gui == null:
		return
	report.new_best = Settings.record_shift(report.total_hkd)
	report.best_hkd = Settings.best_shift_hkd()
	_bank_tally(true)
	_open_menu(report)


## What the run has done since the last save, into the lifetime record (`P3-76`,
## `Q169`). `shift_finished` is 交更's alone. Only a player's run: no menu is a
## scripted one, and a run naming a menu page or the sample is taking a frame.
func _bank_tally(shift_finished: bool) -> void:
	if (
		_gui == null
		or not is_instance_valid(level.fares)
		or not Cmdline.value(StartMenu.PAGE_ARG).is_empty()
		or not Cmdline.value(StartMenu.SAMPLE_ARG).is_empty()
	):
		return
	Settings.bank_tally(level.fares.tally, shift_finished)


## A fresh menu over the parked level: on the report, or on HOME for none.
func _open_menu(report: StartMenu.Report) -> void:
	var shown := StartMenu.new()
	shown.name = "StartMenu"
	shown.report = report
	_gui.add_child(shown)
	_follow_menu(shown)


## The HUD built every language-bound label at boot from `Locale`, so a new
## language is a new HUD: the old one is retired and a fresh one readied in its
## place, hidden until start like the first. Re-instanced rather than re-labelled
## inside `hud.gd`, so the HUD keeps one build path and the check that grades it
## grades the one that ships.
func _on_language_changed(_code: String) -> void:
	_renew_hud()


func _renew_hud() -> void:
	if not is_instance_valid(hud):
		return
	var gui: Node = hud.get_parent()
	var retired: Hud = hud
	retired.name = "HudRetired"
	retired.queue_free()
	hud = Hud.new()
	hud.name = "Hud"
	gui.add_child(hud)
	hud.visible = false
	_hand_over()
