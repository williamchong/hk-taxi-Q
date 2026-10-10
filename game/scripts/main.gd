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


func _ready() -> void:
	# After `World` and `GUI` have readied: children ready first, so the level
	# has placed its car and the HUD has built its plate before this runs.
	if hud == null:
		push_warning("Main has no HUD assigned; the plate and the speed will not draw.")
	if level == null:
		push_warning("Main has no level assigned; the HUD has no car to read.")
		return
	_hand_over()
	level.shift_over.connect(_on_shift_over)

	# Under `--menu=off` the menu frees itself in its own `_ready`, which is
	# deferred to the end of this frame, so the export still points at a node
	# that is leaving: its own queued state is the one answer, not a second
	# read of the flag.
	if menu == null or menu.is_queued_for_deletion():
		return
	_gui = menu.get_parent()
	level.park()
	if is_instance_valid(hud):
		hud.visible = false
	_follow_menu(menu)


func _follow_menu(shown: StartMenu) -> void:
	shown.started.connect(_on_started)
	shown.language_changed.connect(_on_language_changed)


## The HUD reads the level's car and fare loop. Guarded for `--hud=off`, where
## the HUD has freed itself before this runs.
func _hand_over() -> void:
	if not is_instance_valid(hud):
		return
	hud.vehicle = level.vehicle
	hud.fares = level.fares
	hud.clock = level.clock


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
	var fares: FareSystem = level.fares if is_instance_valid(level.fares) else null
	var total: float = fares.earned_hkd if fares != null else 0.0
	var delivered: int = fares.deliveries if fares != null else 0
	var walked: int = fares.bails if fares != null else 0
	print("shift over: HK$%.1f, %d delivered, %d walked" % [total, delivered, walked])
	level.park()
	_ended = true
	if is_instance_valid(hud):
		hud.visible = false
	if _gui == null:
		return
	var report := StartMenu.Report.new()
	report.total_hkd = total
	report.deliveries = delivered
	report.bails = walked
	report.new_best = Settings.record_shift(total)
	report.best_hkd = Settings.best_shift_hkd()
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
