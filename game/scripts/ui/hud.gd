extends CanvasLayer
## The player's HUD: how fast, and what street (`P3-24`).
##
## Two readouts ship and three slots are reserved. `P3-5a` fills the timer and
## the fare meter when there is a fare to run; `P3-5b` fills the minimap.
## The slots are laid out and checked **now**, empty, because a HUD that grows
## into whatever space is left is how the touch controls end up under the speed.
##
## **Everything positional comes from `tuning/hud_layout.tres`**, including the
## rects `P2-4` will put thumbs on, and `tools/verify_hud.gd` asserts nothing
## here sits under one. See `hud_layout.gd` for why that contract is written by
## the task that is not building the second half of it — and for why a thumb and
## a tap zone are two different rects.
##
## ⚠️ **Below the dev chrome, deliberately.** `DebugHud` is layer 127 and
## `FpsCounter` 128; this is 10. When someone turns on the debug overlay to
## diagnose something, the diagnosis wins the corner. The two do not fight for
## the top-left because this HUD does not use it for anything it needs to read.
##
## ⚠️ **`--hud=off` exists for `P3-9` before it exists for screenshots.**
## `GAME_DESIGN.md` says the player should navigate by memory and `P3-9`'s
## acceptance test is a drive with the direction arrow disabled. A permanent
## street plate is not a direction aid — it says where you are, not where you
## are going — but it is closer to one than that test's premise assumes, so the
## test needs to be able to switch it off. A clean frame for art review is the
## second reason and would not on its own have justified the flag.

## Chooses whether the HUD draws. `--hud=off` for `P3-9` and for art frames.
const HUD_ARG: String = "--hud="

## How often the road graph is asked what is under the car.
##
## Not every frame. `nearest_edge` is budgeted at 1 ms and would be affordable
## per frame, but a street name changes on the scale of a 50-150 m block and
## there is nothing to buy by asking 60 times a second. At 5 Hz and 100 kph a
## sample is 5.5 m apart, which is far finer than the thing being measured.
const STREET_HZ: float = 5.0

## Speed is sampled faster — it is a number that genuinely changes every frame —
## but still not per frame, because the last digit of an integer kph readout
## strobes unreadably when it is redrawn at 60 Hz.
const SPEED_HZ: float = 10.0

var _layout: HudLayout = null
var _style: HudStyle = null
var _tracker: StreetTracker = null
var _graph: RoadGraph = null
var _car: VehicleController = null

var _plate: ChamferPanel = null
var _plate_en: Label = null
var _plate_zh: Label = null
## Kept so the plate can be re-cut to each new name, along with the edge
## `_place` pinned it to. Captured once rather than read back off the Control:
## `_fit_plate` writes those same offsets, so re-deriving them from the node
## would drift a little further from the layout on every street change.
var _plate_lines: VBoxContainer = null
var _plate_pin := Rect2()
var _plate_anchor_x: float = 0.0
var _speed_value: Label = null
## The chip itself, kept so its bar can be driven every frame.
var _speed_chip: ChamferPanel = null
var _readout: Label = null
## The reserved, empty slots. Outlined under the dev overlay so the space this
## HUD holds for `P3-5a` and `P3-5b` can be SEEN rather than taken on trust
## from a `.tres`, and invisible in every shipped frame.
var _slots: Array[ChamferPanel] = []

var _substitutions: Dictionary = {}
var _street_accum_s: float = 0.0
var _speed_accum_s: float = 0.0
var _shown_speed: String = ""
## Smoothed longitudinal acceleration in m/s², and the last speed it was
## differentiated from, in m/s.
var _accel_mps2: float = 0.0
var _last_speed_ms: float = 0.0
var _shown_fill: float = 0.0


func _ready() -> void:
	layer = 10
	# ⚠️ **`set_process(false)` before every early return, and it is not
	# belt-and-braces.** `queue_free()` is deferred: the node survives to the end
	# of the frame and `_process` runs once more on it, against labels `_build`
	# never created. `--hud=off` therefore crashed on `_speed_value.text` with
	# the HUD apparently working perfectly in every other run — and Godot exits
	# **0** on a script error, so only `drive.sh`'s own stderr grep caught it.
	if not _wanted() or not _load_layout():
		set_process(false)
		# Freed rather than parked. `DebugHud` keeps itself alive because two
		# scripts hold a reference to that singleton and a freed autoload turns
		# their calls into runtime errors; nothing holds a reference to this.
		queue_free()
		return

	_tracker = StreetTracker.new()
	_graph = RoadGraph.shared()
	_build()

	# Registered with the dev overlay rather than drawn here: the raw-versus-
	# displayed comparison is a diagnostic, and `DebugHud` already owns where
	# diagnostics go and what they look like.
	_readout = Label.new()
	_readout.name = "HudReadout"
	DebugHud.attach_readout(_readout)


func _exit_tree() -> void:
	# A label parented to the autoload outlives this scene and would otherwise
	# stack up one per scene change. `debug_hud.gd::attach_readout` says so.
	if _readout != null:
		DebugHud.detach_readout(_readout)
		_readout = null


## The layout, or false having said why. Split out of `_ready` so the two ways
## this HUD declines to exist share one teardown.
func _load_layout() -> bool:
	_layout = load(HudLayout.PATH) as HudLayout
	if _layout == null:
		push_warning("hud: %s did not load; no HUD this run" % HudLayout.PATH)
		return false
	_style = load(HudStyle.PATH) as HudStyle
	if _style == null:
		push_warning("hud: %s did not load; no HUD this run" % HudStyle.PATH)
		return false
	return true


## `--hud=off` turns it off; anything else, including nothing, leaves it on.
##
## ⚠️ **Headless is not a reason to skip it here**, unlike `DebugHud`. A verify
## tool that instantiates a drive scene should still get a HUD that built its
## nodes, because "the HUD failed to build" is exactly the kind of thing a
## headless check should be able to notice. Nothing is rasterised either way.
func _wanted() -> bool:
	return DebugHud.cmdline_value(HUD_ARG).to_lower() != "off"


func _build() -> void:
	var plate_tuning: Dictionary = StreetPlate.load_tuning()
	_substitutions = plate_tuning.get("substitutions", {}) as Dictionary
	# ⚠️ Skipped where there is no city, and that is not a micro-optimisation:
	# the face is **6.4 MB**, and without a road graph no street ever resolves,
	# so the plate stays hidden for the life of the run. That is every headless
	# verify tool that instantiates a drive scene, and every clone that has not
	# built a region. `_wanted()` deliberately does not skip headless, so this is
	# the guard that keeps it honest.
	var font_zh: Font = null
	if _graph != null and not _graph.is_empty():
		font_zh = load(plate_tuning.get("font_zh", "")) as Font
	if font_zh == null and _graph != null and not _graph.is_empty():
		# Not fatal, and loud. The English line still draws; the Chinese line
		# would be a row of tofu, which reads as a bug in the game rather than a
		# missing asset, so it is refused instead.
		push_warning("hud: the plate's Chinese font did not load; drawing English only")

	# One root Control so the safe-area inset is applied once rather than per
	# slot. Everything below anchors inside it.
	var root := Control.new()
	root.name = "Safe"
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	_inset_for_safe_area(root)

	# ---- the street plate: the CITY's voice ----
	#
	# A white field with a hard black keyline, which is what a Wan Chai street
	# name plate actually is, cut to the name on it by `_fit_plate`. The chamfer is the HUD's one shared shape, so the
	# sign and the instrument read as one family without being one colour.
	_plate = ChamferPanel.new()
	_plate.name = "StreetPlate"
	_plate.chamfer_px = _style.chamfer_px
	_plate.fill = _style.plate_field
	_plate.edge = _style.plate_edge
	_plate.edge_px = _style.edge_px
	# Hidden until there is a street. On a clone with no generated city there
	# never is one, and an empty white sign is worse than nothing.
	_plate.visible = false
	_place(root, _plate, _layout.street_plate)
	_plate_anchor_x = _plate.anchor_left
	_plate_pin = Rect2(
		_plate.offset_left,
		_plate.offset_top,
		_plate.offset_right - _plate.offset_left,
		_plate.offset_bottom - _plate.offset_top
	)

	_plate_lines = _lines(_plate, 0)
	var lines: VBoxContainer = _plate_lines

	# ⚠️ **Always centred, whichever screen edge the plate hangs off.** The
	# lettering briefly followed the pinned edge, which right-aligned 博覽道東
	# under EXPO DRIVE EAST — two lines of very different width ragged against
	# one side. A street sign centres its lines; the PANEL moves, the words do
	# not.
	_plate_en = _label("English", _style.plate_size_en, _style.plate_ink)
	_plate_en.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	lines.add_child(_plate_en)

	_plate_zh = _label("Chinese", _style.plate_size_zh, _style.plate_ink)
	_plate_zh.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	if font_zh != null:
		# Overridden on this label alone. The English line keeps the theme's
		# Noto Sans on purpose — a real Hong Kong plate carries a Latin
		# grotesque above a Chinese Kai, so two typefaces is the accurate
		# answer rather than an inconsistency to tidy up.
		_plate_zh.add_theme_font_override(&"font", font_zh)
	lines.add_child(_plate_zh)

	# ---- speed: the CAR's voice ----
	#
	# Dark chip, light numerals, one saturated bar along the bottom. The
	# opposite treatment to the plate on purpose, so a glance tells the two
	# apart before it has read either.
	_speed_chip = ChamferPanel.new()
	_speed_chip.name = "Speed"
	_speed_chip.chamfer_px = _style.chamfer_px
	_speed_chip.fill = _style.chip_field
	_speed_chip.edge = Color.TRANSPARENT
	_speed_chip.accent = _style.accent
	_speed_chip.accent_negative = _style.accent_negative
	_speed_chip.accent_track = _style.accent_track
	_speed_chip.accent_px = _style.accent_px
	_place(root, _speed_chip, _layout.speed)

	var speed_lines: VBoxContainer = _lines(_speed_chip, _style.speed_line_tighten)

	_speed_value = _label("Value", _style.speed_size, _style.chip_ink)
	speed_lines.add_child(_speed_value)

	var unit: Label = _label("Unit", _style.speed_unit_size, _style.chip_muted)
	unit.text = "km/h"
	speed_lines.add_child(unit)

	# ---- the reserved slots ----
	#
	# ⚠️ Built as named, empty Controls rather than left out, and **outlined under
	# the dev overlay**. A slot that exists only as a rect in a `.tres` is a slot
	# the next task has to take on trust; one that can be switched on and looked
	# at is one anybody can check. Invisible — and free — in every shipped frame.
	var reserved: Dictionary[String, Rect2] = _layout.reserved_slots()
	for slot_name: String in reserved:
		var slot := ChamferPanel.new()
		slot.name = slot_name
		slot.chamfer_px = _style.chamfer_px
		slot.fill = _style.slot_fill
		slot.edge = _style.slot_edge
		slot.edge_px = _style.slot_edge_px
		_place(root, slot, reserved[slot_name])
		_slots.append(slot)
	_show_slots()
	DebugHud.view_changed.connect(_show_slots)


## A centred line of HUD text. Four of these differed only in a name, a size and
## a colour.
static func _label(node_name: String, size: int, ink: Color) -> Label:
	var label := Label.new()
	label.name = node_name
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_color_override(&"font_color", ink)
	label.add_theme_font_size_override(&"font_size", size)
	return label


## A panel's stack of lines, centred in it.
static func _lines(panel: Control, separation: int) -> VBoxContainer:
	var box := VBoxContainer.new()
	box.name = "Lines"
	box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	box.set_anchors_preset(Control.PRESET_FULL_RECT)
	box.add_theme_constant_override(&"separation", separation)
	box.alignment = BoxContainer.ALIGNMENT_CENTER
	panel.add_child(box)
	return box


## Cut the plate to the name on it, about the centre of its reserved box.
##
## A street sign is made to fit its lettering. Drawing every name in one
## fixed-width slab is what made this read as a dialog: `SHARP STREET` sat in
## the middle of a plate sized for `CROSS HARBOUR TUNNEL`, with the white doing
## nothing on either side of it.
##
## ⚠️ **Clamped to the reserved width**, so a long name cannot grow the plate
## out of the box `verify_hud.gd` grades — the reservation stays the worst case
## rather than becoming a suggestion. The `Label`s wrap inside it if one ever
## does exceed it.
##
## ⚠️ **The speed deliberately does NOT do this.** An instrument has a fixed
## bezel; a readout whose panel resized as the car passed 100 kph would twitch
## at exactly the moment it is being read.
func _fit_plate() -> void:
	var box: Rect2 = _layout.street_plate
	var wanted: Vector2 = _plate_lines.get_combined_minimum_size() + _style.plate_pad * 2.0
	var width: float = minf(wanted.x, box.size.x)
	var height: float = minf(maxf(wanted.y, 0.0), box.size.y)

	# Grows away from whichever edge `_place` pinned it to, so the plate keeps
	# the screen edge it is aligned against however long the name is — and so
	# moving it in the `.tres` needs no code change here, which is the whole
	# point of the layout being data.
	if is_equal_approx(_plate_anchor_x, 1.0):
		_plate.offset_right = _plate_pin.end.x
		_plate.offset_left = _plate_pin.end.x - width
	elif is_zero_approx(_plate_anchor_x):
		_plate.offset_left = _plate_pin.position.x
		_plate.offset_right = _plate_pin.position.x + width
	else:
		var centre: float = _plate_pin.position.x + _plate_pin.size.x * 0.5
		_plate.offset_left = centre - width * 0.5
		_plate.offset_right = centre + width * 0.5
	_plate.offset_bottom = _plate_pin.end.y
	_plate.offset_top = _plate_pin.end.y - height


## The reserved slots follow the dev overlay's readouts: off in every shipped
## frame, on when someone is asking where the space went.
func _show_slots() -> void:
	var showing: bool = DebugHud.shows_readouts()
	for slot: ChamferPanel in _slots:
		slot.visible = showing


## Put `control` where the layout says, converting a design-space rect into
## anchors so the slot keeps its corner when the window is not 16:9.
##
## The anchor is **derived** from where the rect sits rather than passed in: a
## slot in the left third holds the left edge, one in the right third holds the
## right edge, and anything spanning the middle holds the centre. Per-slot
## anchor arguments would be a second table to keep in step with the first.
func _place(parent: Control, control: Control, design: Rect2) -> void:
	parent.add_child(control)
	var size: Vector2 = _layout.design_size
	var horizontal: Vector2 = _axis(design.position.x, design.end.x, size.x)
	var vertical: Vector2 = _axis(design.position.y, design.end.y, size.y)
	control.anchor_left = horizontal.x
	control.anchor_right = horizontal.x
	control.anchor_top = vertical.x
	control.anchor_bottom = vertical.x
	control.offset_left = design.position.x - horizontal.y
	control.offset_right = design.end.x - horizontal.y
	control.offset_top = design.position.y - vertical.y
	control.offset_bottom = design.end.y - vertical.y


## Returns `(anchor, the design coordinate that anchor sits at)` for one axis.
static func _axis(from: float, to: float, extent: float) -> Vector2:
	if to <= extent * 0.35:
		return Vector2(0.0, 0.0)
	if from >= extent * 0.65:
		return Vector2(1.0, extent)
	return Vector2(0.5, extent * 0.5)


## Pull the whole HUD in by the display's safe area, for a notch or a rounded
## corner.
##
## ⚠️ **Measured in screen pixels and applied in canvas units**, which are not
## the same thing under `canvas_items` stretch — the ratio is what converts
## them. Applying the raw pixel inset would over-inset by the stretch factor on
## every device whose panel is not 1920 wide, which is all of them.
func _inset_for_safe_area(root: Control) -> void:
	var screen: Vector2i = DisplayServer.screen_get_size()
	var window: Vector2i = DisplayServer.window_get_size()
	if screen.x <= 0 or screen.y <= 0 or window.x <= 0 or window.y <= 0:
		return

	# 🔴 **The safe area is measured against the SCREEN, not against the window,
	# and conflating the two deletes the whole HUD.** `get_display_safe_area()`
	# returns a rect in display coordinates; on a handset the window fills the
	# display and the two frames coincide, which is the case the API is for. In
	# a desktop window they do not — the window is smaller than the screen — so
	# `screen - window` came out *negative*, the root Control grew larger than
	# the viewport instead of smaller, and everything anchored to an edge was
	# pushed off it. The frame renders perfectly with no HUD on it, nothing is
	# logged, and `check.sh` is green: this was found by looking at a screenshot
	# and by nothing else.
	#
	# So the inset applies only where it means anything — a window that fills
	# the display — and every side is clamped at zero so that no arithmetic here
	# can ever make the HUD bigger than the screen again.
	if window != screen:
		return

	var safe: Rect2i = DisplayServer.get_display_safe_area()
	var canvas: Vector2 = root.get_viewport_rect().size
	# Not `scale` — `CanvasLayer` already has one, and the warnings sweep
	# promotes shadowing to an error. Naming it for what it is anyway. The ratio
	# converts screen pixels into canvas units, which `canvas_items` stretch
	# makes different numbers on every panel that is not 1920 wide.
	var canvas_per_pixel := Vector2(canvas.x / float(screen.x), canvas.y / float(screen.y))
	root.offset_left = maxf(0.0, float(safe.position.x)) * canvas_per_pixel.x
	root.offset_top = maxf(0.0, float(safe.position.y)) * canvas_per_pixel.y
	root.offset_right = -maxf(0.0, float(screen.x - safe.end.x)) * canvas_per_pixel.x
	root.offset_bottom = -maxf(0.0, float(screen.y - safe.end.y)) * canvas_per_pixel.y


func _process(delta: float) -> void:
	_update_accel(delta)
	_update_speed(delta)
	_update_street(delta)


## Drive the chip's bar from how hard the car is gaining or losing speed.
##
## **Acceleration, and deliberately not engine revs.** A rev counter is what an
## MT driver reads this bar as, but this car has no gearbox: `VehicleWheel3D`
## publishes `get_rpm()` and without gearing it is proportional to road speed,
## so a rev bar would be the number directly above it drawn a second way. What
## the driver cannot already see is whether the car is *gaining* — the bar is
## empty at a steady 80 kph, fills under power, and swings the other way under
## braking.
##
## ⚠️ **Every frame, not on the 10 Hz speed gate.** A differentiated velocity
## sampled at 10 Hz is a staircase; the smoothing needs the small `delta` to be
## a filter rather than a lag. The work is one subtraction and one lerp.
func _update_accel(delta: float) -> void:
	var car: VehicleController = _vehicle()
	if car == null or delta <= 0.0:
		return
	var speed_ms: float = car.forward_speed_kph() / 3.6
	var raw: float = (speed_ms - _last_speed_ms) / delta
	_last_speed_ms = speed_ms
	# Exponential, framerate-independent: `delta / tau` clamped, so a slow frame
	# catches up rather than overshooting.
	var follow: float = clampf(delta / maxf(_style.accel_smoothing_s, 0.001), 0.0, 1.0)
	_accel_mps2 = lerpf(_accel_mps2, raw, follow)

	var fill: float = clampf(_accel_mps2 / maxf(_style.accel_full_scale_mps2, 0.001), -1.0, 1.0)
	# Assigned only on a visible change: the setter queues a redraw, and a
	# parked car would otherwise redraw the panel sixty times a second to draw
	# the same bar.
	if absf(fill - _shown_fill) < 0.004:
		return
	_shown_fill = fill
	_speed_chip.accent_fill = fill


func _update_speed(delta: float) -> void:
	_speed_accum_s += delta
	if _speed_accum_s < 1.0 / SPEED_HZ:
		return
	_speed_accum_s = 0.0

	var car: VehicleController = _vehicle()
	if car == null:
		return
	# `forward_speed_kph` is signed — negative reversing. Shown as a magnitude
	# with an R, because "-12" is a reading nobody takes off a speedometer.
	var speed: float = car.forward_speed_kph()
	# Guarded on the rendered STRING, not on the magnitude. Keying on the
	# rounded integer alone let a sign flip between two samples of equal speed
	# — −12 to +12 — compare equal and leave the readout saying `R 12` while
	# driving forward.
	var shown: int = roundi(absf(speed))
	var text: String = ("R %d" % shown) if speed < -1.0 else str(shown)
	if text == _shown_speed:
		return
	# Assigned only on a change: setting `Label.text` is a TextServer reshape,
	# and this is a node that runs for the whole session.
	_shown_speed = text
	_speed_value.text = text


func _update_street(delta: float) -> void:
	_street_accum_s += delta
	if _street_accum_s < 1.0 / STREET_HZ:
		return
	var elapsed: float = _street_accum_s
	_street_accum_s = 0.0

	var car: VehicleController = _vehicle()
	if car == null or _graph == null or _graph.is_empty():
		return

	var hit: RoadGraph.Hit = _graph.nearest_edge(car.global_position, -car.global_transform.basis.z)
	# `elapsed` and not `delta`: the tracker's dwell is in seconds of real time,
	# and feeding it one frame's worth per sample would stretch a 0.6 s dwell to
	# 3 s at 5 Hz. The bug this avoids looks like "the plate is slow", which is
	# indistinguishable from the dwell simply being too long.
	_tracker.sample(hit.edge_id, hit.road_name_en, hit.road_name_zh, elapsed)
	# Driven from here rather than from `_process`: every value it reports is
	# sampled at `STREET_HZ`, so rebuilding it per frame would reshape three
	# identical lines 55 times a second — the cost `_update_speed` guards
	# against, paid on the overlay that is on precisely when someone is
	# measuring.
	_update_readout(hit)

	if not _tracker.has_street():
		return
	if not _plate.visible:
		_plate.visible = true
	if _plate_en.text != _tracker.street_en:
		_plate_en.text = _tracker.street_en
		_plate_zh.text = StreetPlate.substitute(_tracker.street_zh, _substitutions)
		_fit_plate()


## The raw graph answer beside the displayed one, and the change count.
##
## The raw side is what makes a wrong plate reportable rather than a feeling:
## `street_tracker.gd` records why `changes` is the number that grades this, and
## the comparison here is how a drive is checked against it.
func _update_readout(hit: RoadGraph.Hit) -> void:
	if _readout == null or not DebugHud.shows_readouts():
		return
	var raw: String = hit.road_name_en if not hit.road_name_en.is_empty() else "(unnamed)"
	if hit.edge_id < 0:
		raw = "(no edge)"
	_readout.text = (
		"street  shown %s (e%d)\n        raw   %s (e%d)\n        changes %d"
		% [_tracker.street_en, _tracker.edge_id, raw, hit.edge_id, _tracker.changes]
	)


## `is_instance_valid` rather than a null check: on a scene change the car this
## followed is freed and the stale reference still reads as non-null. The same
## trap `debug_hud.gd::_process` documents.
func _vehicle() -> VehicleController:
	if not is_instance_valid(_car):
		_car = null
	if _car == null:
		_car = VehicleController.first_in(get_tree())
	return _car
