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
## ⚠️ **Below the dev chrome, deliberately.** `DebugHud` is layer 127, frame
## counter included; this is 10. When someone turns on the debug overlay to
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
var _monitor: WrongWayMonitor = null
var _graph: RoadGraph = null
var _car: VehicleController = null

var _plate: ChamferPanel = null
var _plate_en: Label = null
var _plate_zh: Label = null
## Kept so the plate can be re-cut to each new name.
var _plate_lines: VBoxContainer = null
var _speed_value: Label = null
## The chip itself, kept so its bar can be driven every frame.
var _speed_chip: AccentBar = null
var _readout: Label = null
## The reserved, empty slots. Outlined under the dev overlay so the space this
## HUD holds for `P3-5a` and `P3-5b` can be SEEN rather than taken on trust
## from a `.tres`, and invisible in every shipped frame.
var _slots: Array[ChamferPanel] = []
## The wrong-way sign. Hidden in every ordinary frame.
var _warning: NoEntryIcon = null

var _substitutions: Dictionary = {}
var _street_accum_s: float = 0.0
## Where the blink is in its own cycle, in seconds. Reset when the sign comes
## down so the next raise starts LIT — otherwise an alarm can be born dark and
## appear to arrive up to half a period late, which is the half of the cycle it
## can least afford.
var _blink_s: float = 0.0
var _speed_accum_s: float = 0.0
var _shown_speed: String = ""
## Smoothed longitudinal acceleration in m/s², and the last speed it was
## differentiated from, in m/s.
var _accel_mps2: float = 0.0
var _last_speed_ms: float = 0.0


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
	_monitor = WrongWayMonitor.new()
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
	var root: Control = HudLayout.safe_root(self)

	# ---- the street plate: the CITY's voice ----
	#
	# A white field with a hard black keyline, which is what a Wan Chai street
	# name plate actually is, cut to the name on it by `_fit_plate`. The chamfer
	# is the HUD's one shared shape, so the
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
	_layout.place(root, _plate, _layout.street_plate)

	_plate_lines = _lines(_plate, 0)

	_plate_en = _label("English", _style.plate_size_en, _style.plate_ink)
	_plate_lines.add_child(_plate_en)

	_plate_zh = _label("Chinese", _style.plate_size_zh, _style.plate_ink)
	if font_zh != null:
		# Overridden on this label alone. The English line keeps the theme's
		# Noto Sans on purpose — a real Hong Kong plate carries a Latin
		# grotesque above a Chinese Kai, so two typefaces is the accurate
		# answer rather than an inconsistency to tidy up.
		_plate_zh.add_theme_font_override(&"font", font_zh)
	_plate_lines.add_child(_plate_zh)

	# ---- speed: the CAR's voice ----
	#
	# Dark chip, light numerals, one saturated bar along the bottom. The
	# opposite treatment to the plate on purpose, so a glance tells the two
	# apart before it has read either.
	_speed_chip = AccentBar.new()
	_speed_chip.name = "Speed"
	_speed_chip.chamfer_px = _style.chamfer_px
	_speed_chip.fill = _style.chip_field
	_speed_chip.edge = Color.TRANSPARENT
	_speed_chip.accent = _style.accent
	_speed_chip.accent_negative = _style.accent_negative
	_speed_chip.accent_track = _style.accent_track
	_speed_chip.accent_px = _style.accent_px
	_layout.place(root, _speed_chip, _layout.speed)

	var speed_lines: VBoxContainer = _lines(_speed_chip, _style.speed_line_tighten)

	_speed_value = _label("Value", _style.speed_size, _style.chip_ink)
	speed_lines.add_child(_speed_value)

	var unit: Label = _label("Unit", _style.speed_unit_size, _style.chip_muted)
	unit.text = "km/h"
	speed_lines.add_child(unit)

	# ---- the wrong way: the CITY refusing ----
	#
	# NO ENTRY, the 179 plates of it already standing out there, blinking at the
	# top of the frame. No panel behind it and no lettering on it — see
	# `no_entry_icon.gd` for why a disc is admissible in a UI of cut polygons, and
	# `hud_layout.gd::wrong_way` for why an alarm may share a band that a standing
	# readout was refused.
	_warning = NoEntryIcon.new()
	_warning.name = "WrongWay"
	_warning.disc = _style.warn_disc
	# The city's white, already declared once for the plate. See `hud_style.gd`.
	_warning.bar = _style.plate_field
	_warning.bar_length = _style.warn_bar_length
	_warning.bar_thickness = _style.warn_bar_thickness
	_warning.visible = false
	_layout.place(root, _warning, _layout.wrong_way)

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
		_layout.place(root, slot, reserved[slot_name])
		_slots.append(slot)
	_show_slots()
	DebugHud.view_changed.connect(_show_slots)


## A centred line of HUD text. Four of these differed only in a name, a size and
## a colour.
##
## ⚠️ **Centred, and the plate must not override it.** The plate's lettering
## briefly followed whichever screen edge the panel was pinned to, which
## right-aligned 博覽道東 under EXPO DRIVE EAST — two lines of very different
## width ragged against one side. A sign centres its lines: the panel moves, the
## words do not.
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
	var height: float = minf(wanted.y, box.size.y)

	# Grows away from whichever edge the layout pinned it to, so the plate keeps
	# the screen edge it is aligned against however long the name is — and so
	# moving it in the `.tres` needs no code change here, which is the whole
	# point of the layout being data.
	#
	# ⚠️ **The anchor comes from the FULL rect, not the shrunk one.** `HudLayout.axis`
	# picks its edge by which third of the screen the box falls in, and a plate
	# cut down to a short name can land in a different third than the slot it
	# was placed in — which would re-pin it to the opposite edge mid-drive.
	var horizontal: Vector2 = HudLayout.axis(box.position.x, box.end.x, _layout.design_size.x)
	_layout.offsets(
		_plate,
		Rect2(
			box.position.x + (box.size.x - width) * horizontal.x, box.end.y - height, width, height
		),
		_layout.street_plate
	)


## The reserved slots follow the dev overlay's readouts: off in every shipped
## frame, on when someone is asking where the space went.
func _show_slots() -> void:
	var showing: bool = DebugHud.shows_readouts()
	for slot: ChamferPanel in _slots:
		slot.visible = showing


func _physics_process(delta: float) -> void:
	_update_accel(delta)


## ⚠️ **The acceleration bar is driven from `_physics_process`, not here.** See
## `_update_accel`; `linear_velocity` only changes on a physics tick, so a
## render-rate differentiator divides a real change by the wrong interval.
func _process(delta: float) -> void:
	_update_speed(delta)
	_update_street(delta)
	# ⚠️ Every frame, unlike the two above, and it is the one thing here that has
	# to be. The monitor is sampled at `STREET_HZ` with everything else, but the
	# blink is an animation: gating it at 5 Hz would quantise a 2 Hz square wave
	# onto 200 ms steps and make the alarm stutter rather than pulse.
	_update_warning(delta)


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
## 🔴 **On the physics tick, because that is the only tick the input changes
## on.** Physics and rendering both run at 60 Hz and are *not* phase-locked, and
## nothing interpolates between them — so differentiating in `_process` gave
## some frames no velocity change at all and the next frame two ticks' worth,
## roughly doubling the variance of a signal this file already has to filter
## hard. `main.tscn` puts `GUI` after `World`, so the car's own `_physics_process`
## has already written `speed_kph` when this reads it.
##
## ⚠️ **`car.speed_kph`, never `forward_speed_kph()`.** `vehicle_controller.gd`
## caches the first for exactly this reason — "everything that wants the car's
## speed wants the same number in the same tick" — and the second recomputes a
## dot product and a global basis per call.
func _update_accel(delta: float) -> void:
	var car: VehicleController = _vehicle()
	if car == null or delta <= 0.0:
		return
	var speed_ms: float = car.speed_kph / 3.6
	var raw: float = (speed_ms - _last_speed_ms) / delta
	_last_speed_ms = speed_ms

	# ⚠️ **`1 - exp(-dt/tau)`, not `dt/tau`.** The linear form is that curve's
	# first-order approximation and it is 4.7% low at 60 fps, 9% at 30 and 19%
	# at 15 — so the effective time constant *shortens* as frames are dropped
	# and the bar gets jumpier exactly when the game is struggling, which is the
	# opposite of what a smoothing filter is for. The exact form also needs no
	# clamp: it is in [0, 1) for every non-negative delta.
	var follow: float = 1.0 - exp(-delta / maxf(_style.accel_smoothing_s, 0.001))
	_accel_mps2 = lerpf(_accel_mps2, raw, follow)

	var fill: float = clampf(_accel_mps2 / maxf(_style.accel_full_scale_mps2, 0.001), -1.0, 1.0)
	# Assigned only on a visibly different reading: the setter queues a redraw,
	# and the threshold is one pixel of the bar's own half-reach rather than a
	# chosen constant, so it stays sub-pixel whatever the chip is resized to.
	var step: float = 1.0 / maxf(_layout.speed.size.x * 0.5, 1.0)
	if absf(fill - _speed_chip.accent_fill) < step:
		return
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
	var speed: float = car.speed_kph
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
		# 🔴 **Not a bare return.** Freezing the monitor here left a sign that
		# happened to be up blinking for ever on a scene change, with the car that
		# earned it already freed — the latched siren `wrong_way_monitor.gd` is
		# written against, through the one door its miss rule does not cover.
		_monitor.stand_down(elapsed)
		return

	# One heading, read once: `nearest_edge` resolves a two-way edge against it and
	# the monitor judges the nose by it, and they must be the same vector.
	var heading: Vector3 = -car.global_transform.basis.z
	var hit: RoadGraph.Hit = _graph.nearest_edge(car.global_position, heading)
	# Fed the same `Hit` the plate is, so the warning costs no second query on a
	# path budgeted at 1 ms. ⚠️ **The heading raises the sign and the velocity can
	# only withhold it** — reversing while pointed the legal way is not something
	# a NO ENTRY has anything useful to say about. `wrong_way_monitor.gd` is
	# written around that and records why it was built the other way round first.
	_monitor.sample(hit.one_way, hit.forward, heading, car.linear_velocity, elapsed)
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
	var law: String = "one-way" if hit.one_way else "two-way"
	# Both lines describe the same miss, so they are decided in one place: two
	# guards on `edge_id` are two chances to disagree about what a miss looks like.
	if hit.edge_id < 0:
		raw = "(no edge)"
		law = "no edge"
	# ⚠️ The monitor's raw angle beside its verdict, for the same reason the raw
	# street name sits beside the shown one: `Q62` leaves no published truth to
	# grade either against, so what makes a wrong answer reportable is the input
	# it was reached from. `raises` against streets-driven is the number a drive
	# is checked on — see `wrong_way_monitor.gd`.
	var angle: String = ("%.0f deg" % _monitor.angle_deg) if _monitor.has_angle() else "--"
	_readout.text = (
		(
			"street  shown %s (e%d)\n        raw   %s (e%d)\n        changes %d"
			+ "\nway     %s (%s, %s), raises %d"
		)
		% [
			_tracker.street_en,
			_tracker.edge_id,
			raw,
			hit.edge_id,
			_tracker.changes,
			"WRONG" if _monitor.wrong_way else "ok",
			law,
			angle,
			_monitor.raises,
		]
	)


## Blink the sign while the monitor says the car is going the wrong way.
##
## ⚠️ **Blinked by toggling `visible`, not by animating `modulate`.** An alpha
## ramp queues a `_draw` on every frame for the whole session on a node that is
## invisible in almost all of them; `visible` re-composites and redraws nothing,
## and the sign's geometry never changes.
##
## The duty cycle is square and half-on, which is what an alarm looks like, and
## `warn_blink_hz` is capped by `verify_hud.gd` well under the photosensitivity
## threshold rather than left to taste. See `hud_style.gd`.
func _update_warning(delta: float) -> void:
	var lit: bool = false
	if _monitor.wrong_way:
		var period: float = 1.0 / maxf(_style.warn_blink_hz, 0.001)
		_blink_s = fmod(_blink_s + delta, period)
		lit = _blink_s < period * 0.5
	else:
		_blink_s = 0.0

	# Assigned only on a change, like every other write in this file: a node that
	# runs for the whole session should not touch the scene tree 60 times a
	# second to say nothing.
	if _warning.visible != lit:
		_warning.visible = lit


## `is_instance_valid` rather than a null check: on a scene change the car this
## followed is freed and the stale reference still reads as non-null. The same
## trap `debug_hud.gd::_process` documents.
func _vehicle() -> VehicleController:
	if not is_instance_valid(_car):
		_car = null
	if _car == null:
		_car = VehicleController.first_in(get_tree())
		# ⚠️ A fresh car is not a continuation of the old one's velocity. Without
		# this the first sample after a respawn or a scene change differentiates
		# across the gap and pins the bar hard over for a filter time-constant.
		_last_speed_ms = 0.0 if _car == null else _car.speed_kph / 3.6
	return _car
