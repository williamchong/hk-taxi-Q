class_name Hud
extends CanvasLayer
## The player's HUD: how fast, what street, and the fare (`P3-24`, `P3-5a`).
##
## Two readouts, the minimap (`P3-44`) and the fare's three panels ship — the
## 咪錶 top-right, the tip clock top-left, the bilingual callout top-centre —
## and two slots stay reserved for `P3-2a`/`b` (`Q138`). The fare panels are
## painted from `FareFace`, which decides every string; this file only puts
## them in their rects.
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

## `--minimap=off` takes the map alone (`Q136`). `GAME_DESIGN.md`'s acceptance
## test disables the minimap and the arrow and says nothing about the speed or
## the plate, so the map cannot share `--hud=off`'s switch.
const MINIMAP_ARG: String = "--minimap="
## How far the route's start must move along its edge before the map's line
## is rebuilt, in metres: under half a pixel at any span the map is drawn at.
const ROUTE_STEP_M: float = 0.5

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

## The language the callout reads in (`Locale`); the plate stays bilingual.
var _language: String = Locale.DEFAULT

var _layout: HudLayout = null
var _style: HudStyle = null
var _tracker: StreetTracker = null
var _monitor: WrongWayMonitor = null
var _tracking: StreetTrackerProfile = null
var _wrong_way: WrongWayProfile = null
var _mapping: MinimapProfile = null
var _graph: RoadGraph = null
## The car this HUD reads, handed in by `Main` (`P5-24`) — the ancestor that
## holds both `World` and `GUI` is the one that knows which car is in play.
## Until then this took the first car in the group, which is a sibling reaching
## across the World / GUI boundary. Null draws the plate empty and the speed at
## rest, never a crash; a level change hands in the next car.
var vehicle: VehicleController = null
## The car the speed filter was last seeded for, so a hand-over reseeds it once.
var _followed: VehicleController = null

## The standalone plate: null where the minimap carries the name instead.
var _plate: ChamferPanel = null
var _plate_en: Label = null
var _plate_zh: Label = null
## What the lettering sits in and what is shown once there is a street: the
## standalone plate, or the minimap's strip where there is a map.
var _plate_host: Control = null
## Kept so the plate can be re-cut to each new name.
var _plate_lines: VBoxContainer = null
var _speed_value: Label = null
## The dial round the numerals. Its needle is driven every frame.
var _dial: SpeedDial = null
## The chip itself, kept so its bar can be driven every frame.
var _speed_chip: AccentBar = null
var _readout: Label = null
## The reserved, empty slots. Outlined under the dev overlay so the space this
## HUD holds for `P3-2a`/`b` can be SEEN rather than taken on trust
## from a `.tres`, and invisible in every shipped frame.
var _slots: Array[ChamferPanel] = []
## The wrong-way sign. Hidden in every ordinary frame.
var _warning: NoEntryIcon = null
## Null under `--minimap=off`, and where there is no city to map.
var _minimap: Minimap = null
## The route last handed to the map (`_paint_route`): its edges and where on
## the first it started.
var _route_edges: PackedInt32Array = PackedInt32Array()
var _route_from_t: float = 0.0

## The fare loop this HUD reads, handed in by `Main` like the car. Null, or a
## system that is not `usable()`, hides the three fare panels.
var fares: FareSystem = null:
	set(value):
		_unfollow_fares()
		fares = value
		_follow_fares()

## What the fare panels say (`fare_face.gd`); rebuilt when a system arrives.
var _face: FareFace = null
var _meter_panel: ChamferPanel = null
var _meter: SevenSegment = null
## The session's takings, under the LED (the user's call: a total beside the
## current fare).
var _total: Label = null
## The tip as it stands, a second LED under the meter's while carrying
## (`P3-49`), with its chip; the row hides between fares.
var _tip_row: HBoxContainer = null
var _tip_caption: Label = null
var _tip: SevenSegment = null
## The tip clock: bare numerals in the middle of the frame, no housing (the
## user's call), outlined so they read on any road.
var _timer_box: HBoxContainer = null
var _timer_value: Label = null
var _callout_panel: ChamferPanel = null
## A caption saying what the box is, the place, and the road under it, in one
## language.
var _caption: Label = null
var _callout: Label = null
var _callout_sub: Label = null
## The meter's tick, flashed under the clock and faded out (the user's call).
var _tick: Label = null
var _tick_s: float = 0.0
## The plate's Chinese face, kept for the callout's second line.
var _font_zh: Font = null

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

	_tracker = StreetTracker.new(_tracking)
	_monitor = WrongWayMonitor.new(_wrong_way)
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
	_tracking = load(StreetTrackerProfile.PATH) as StreetTrackerProfile
	if _tracking == null:
		push_warning("hud: %s did not load; no HUD this run" % StreetTrackerProfile.PATH)
		return false
	_wrong_way = load(WrongWayProfile.PATH) as WrongWayProfile
	if _wrong_way == null:
		push_warning("hud: %s did not load; no HUD this run" % WrongWayProfile.PATH)
		return false
	_mapping = load(MinimapProfile.PATH) as MinimapProfile
	if _mapping == null:
		push_warning("hud: %s did not load; no HUD this run" % MinimapProfile.PATH)
		return false
	return true


## `--hud=off` turns it off; anything else, including nothing, leaves it on.
##
## ⚠️ **Headless is not a reason to skip it here**, unlike `DebugHud`. A verify
## tool that instantiates a drive scene should still get a HUD that built its
## nodes, because "the HUD failed to build" is exactly the kind of thing a
## headless check should be able to notice. Nothing is rasterised either way.
func _wanted() -> bool:
	return Cmdline.value(HUD_ARG).to_lower() != "off"


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
	_font_zh = font_zh
	if font_zh == null and _graph != null and not _graph.is_empty():
		# Not fatal, and loud. The English line still draws; the Chinese line
		# would be a row of tofu, which reads as a bug in the game rather than a
		# missing asset, so it is refused instead.
		push_warning("hud: the plate's Chinese font did not load; drawing English only")

	# One root Control so the safe-area inset is applied once rather than per
	# slot. Everything below anchors inside it.
	var root: Control = HudLayout.safe_root(self)

	# ---- the minimap, and the street name's home ----
	#
	# One component with the street name (the user's call, `Q136`): the map over
	# the union of the two rects, the name in a strip along its bottom. Anchored
	# as the PLATE's rect is — to the bottom edge, with the speed — not as the
	# map's own would be, which spans the middle and would float off the baseline
	# on a tall window. Skipped where there is no city: an empty panel is worse
	# than nothing.
	var mapped: bool = Cmdline.value(MINIMAP_ARG).to_lower() != "off"
	if mapped and _graph != null and not _graph.is_empty():
		_minimap = Minimap.new()
		_minimap.name = "Minimap"
		_minimap.setup(_mapping, _style, _graph, _layout.minimap.size, _layout.street_plate.size.y)
		_layout.place(root, _minimap, _layout.street_plate)
		_layout.offsets(_minimap, _layout.minimap.merge(_layout.street_plate), _layout.street_plate)
		_plate_host = _minimap.strip
	else:
		# ---- the street plate, alone ----
		#
		# Under `--minimap=off`, and on a clone with no city: a panel in the
		# housing's colours, cut to the name on it by `_fit_plate`.
		_plate = ChamferPanel.new()
		_plate.name = "StreetPlate"
		_plate.chamfer_px = _style.chamfer_px
		_plate.fill = _style.plate_field
		_plate.edge = _style.plate_edge
		_plate.edge_px = _style.edge_px
		# Hidden until there is a street, which without a city is never.
		_plate.visible = false
		_layout.place(root, _plate, _layout.street_plate)
		_plate_host = _plate

	_plate_lines = _lines(_plate_host, 0)

	# One language on the plate too (the user's call, `Q142`): the other line
	# is built and hidden, so the tracker still writes both and the language
	# switch is one flag.
	_language = Locale.language()
	_plate_en = _label("English", _style.plate_size_en, _style.plate_ink)
	_plate_en.visible = _language == Locale.ENGLISH
	_plate_lines.add_child(_plate_en)

	_plate_zh = _label("Chinese", _style.plate_size_zh, _style.plate_ink)
	_plate_zh.visible = _language == Locale.CHINESE
	if font_zh != null:
		# Overridden on this label alone. The English line keeps the theme's
		# Noto Sans on purpose — a real Hong Kong plate carries a Latin
		# grotesque above a Chinese Kai, so two typefaces is the accurate
		# answer rather than an inconsistency to tidy up.
		_plate_zh.add_theme_font_override(&"font", font_zh)
	_plate_lines.add_child(_plate_zh)

	# ---- speed: the dashboard ----
	#
	# The cab's other instrument (`Q139`): a dial's ticks and an amber needle
	# over printed numerals, with the acceleration bar along the bottom. NOT the
	# 咪錶's LED — a meter shows the fare, and the one top-right does.
	_speed_chip = AccentBar.new()
	_speed_chip.name = "Speed"
	_speed_chip.chamfer_px = _style.chamfer_px
	_speed_chip.fill = _style.chip_field
	# The same bezel as the map's: one housing, every panel (`Q139`).
	_speed_chip.edge = _style.plate_edge
	_speed_chip.edge_px = _style.edge_px
	_speed_chip.accent = _style.accent
	_speed_chip.accent_negative = _style.accent_negative
	_speed_chip.accent_track = _style.accent_track
	_speed_chip.accent_px = _style.accent_px
	_layout.place(root, _speed_chip, _layout.speed)

	_dial = SpeedDial.new()
	_dial.name = "Dial"
	_dial.full_scale_kph = _style.dial_full_scale_kph
	_dial.major_kph = _style.dial_major_kph
	_dial.minor_kph = _style.dial_minor_kph
	_dial.tick_px = _style.dial_tick_px
	_dial.ink = _style.chip_muted
	_dial.needle = _style.dial_needle
	_dial.set_anchors_preset(Control.PRESET_FULL_RECT)
	_dial.offset_left = _style.dial_inset_px
	_dial.offset_top = _style.dial_inset_px
	_dial.offset_right = -_style.dial_inset_px
	_speed_chip.add_child(_dial)

	# The numerals sit low in the chip, inside the arc's open side.
	var speed_lines: VBoxContainer = _lines(_speed_chip, _style.speed_line_tighten)
	speed_lines.alignment = BoxContainer.ALIGNMENT_END
	speed_lines.offset_bottom = -_style.accent_px * 2.0

	_speed_value = _label("Value", _style.speed_size, _style.chip_ink)
	_speed_value.text = "0"
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
	_warning.bar = _style.warn_bar
	_warning.bar_length = _style.warn_bar_length
	_warning.bar_thickness = _style.warn_bar_thickness
	_warning.visible = false
	_layout.place(root, _warning, _layout.wrong_way)

	# ---- the fare: the 咪錶, the tip clock and the callout ----
	#
	# Top is the fare (`Q138`). Deliberately plain (`P3-5a`'s brief): the
	# reserved rects are taken as they are, and nothing here is laid out.
	# All three hide until a usable `FareSystem` is handed in.
	_meter_panel = _housing("Meter", root, _layout.meter)
	var meter_lines: VBoxContainer = _lines(_meter_panel, 0)
	var meter_row: HBoxContainer = _row(meter_lines, "Row", roundi(_style.plate_pad.y))
	var currency: Label = _label("Currency", _style.meter_label_size, _style.chip_muted)
	currency.text = "HK$"
	currency.size_flags_vertical = Control.SIZE_SHRINK_END
	meter_row.add_child(currency)
	# The LED (`Q139`): the fare's red, and the one place it is spent.
	_meter = _seven_segment("Digits", _style.meter_digit_px, _style.meter_segment_px)
	meter_row.add_child(_meter)
	# The tip, live: the one number on the meter the driver can move at the
	# wheel, on the same LED in the same red (the user's call), smaller.
	_tip_row = _row(meter_lines, "TipRow", roundi(_style.plate_pad.y))
	_tip_row.visible = false
	_tip_caption = _label("TipCaption", _style.meter_label_size, _style.chip_muted)
	_tip_caption.size_flags_vertical = Control.SIZE_SHRINK_END
	_tip_row.add_child(_tip_caption)
	_tip = _seven_segment("TipDigits", _style.tip_digit_px, _style.tip_segment_px)
	_tip_row.add_child(_tip)
	_total = _label("Total", _style.meter_label_size, _style.chip_muted)
	meter_lines.add_child(_total)

	_timer_box = HBoxContainer.new()
	_timer_box.name = "Timer"
	_timer_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_timer_box.alignment = BoxContainer.ALIGNMENT_CENTER
	_timer_box.add_theme_constant_override(&"separation", _style.timer_unit_gap)
	_timer_box.visible = false
	_layout.place(root, _timer_box, _layout.timer)
	_timer_value = _outlined(_label("Value", _style.timer_size, _style.chip_ink))
	_timer_value.size_flags_vertical = Control.SIZE_SHRINK_END
	_timer_box.add_child(_timer_value)
	var seconds: Label = _outlined(_label("Unit", _style.timer_unit_size, _style.chip_muted))
	seconds.text = "秒" if _language == Locale.CHINESE else "s left"
	if _language == Locale.CHINESE and _font_zh != null:
		seconds.add_theme_font_override(&"font", _font_zh)
	# Both on their feet, then the unit lifted by the difference of the two
	# descents: bottoms alone would hang it off the number's descender line.
	var foot := MarginContainer.new()
	foot.name = "UnitFoot"
	foot.mouse_filter = Control.MOUSE_FILTER_IGNORE
	foot.size_flags_vertical = Control.SIZE_SHRINK_END
	var lift: float = (
		_timer_value.get_theme_font(&"font").get_descent(_style.timer_size)
		- seconds.get_theme_font(&"font").get_descent(_style.timer_unit_size)
	)
	foot.add_theme_constant_override(&"margin_bottom", maxi(roundi(lift), 0))
	foot.add_child(seconds)
	_timer_box.add_child(foot)

	# The place over the road (`Q142`), in one language (`Locale`).
	var chinese: bool = _language == Locale.CHINESE
	_callout_panel = _housing("Callout", root, _layout.callout)
	var callout_lines: VBoxContainer = _lines(
		_callout_panel, _sized(_style.callout_line_gap_zh, _style.callout_line_gap)
	)
	_caption = _label(
		"Caption",
		_sized(_style.callout_caption_size_zh, _style.callout_caption_size),
		_style.chip_muted
	)
	callout_lines.add_child(_caption)
	_callout = _label(
		"Place", _sized(_style.callout_size_zh, _style.callout_size_en), _style.plate_ink
	)
	callout_lines.add_child(_callout)
	_callout_sub = _label(
		"Road", _sized(_style.callout_sub_size_zh, _style.callout_sub_size), _style.chip_muted
	)
	callout_lines.add_child(_callout_sub)
	if chinese and _font_zh != null:
		_caption.add_theme_font_override(&"font", _font_zh)
		_callout.add_theme_font_override(&"font", _font_zh)
		_callout_sub.add_theme_font_override(&"font", _font_zh)

	# The tick: "+HK$2.1" under the clock as a unit begins, bare like the
	# clock, faded over `tick_fade_s`. Its alpha is driven in `_process`.
	_tick = _outlined(_label("Tick", _style.tick_size, _style.chip_ink))
	_tick.visible = false
	_layout.place(root, _tick, _layout.tick)

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


## A panel in the housing's colours, placed on its rect and hidden: every fare
## panel starts dark and `_paint_fares` shows what has something to say.
func _housing(node_name: String, root: Control, rect: Rect2) -> ChamferPanel:
	var panel := ChamferPanel.new()
	panel.name = node_name
	panel.chamfer_px = _style.chamfer_px
	panel.fill = _style.plate_field
	panel.edge = _style.plate_edge
	panel.edge_px = _style.edge_px
	panel.visible = false
	_layout.place(root, panel, rect)
	return panel


## A meter's LED in the meter's face — its red, its ghost, its cells and lean —
## at a digit size: the fare's and the tip's differ only there.
func _seven_segment(node_name: String, digit_px: float, segment_px: float) -> SevenSegment:
	var led := SevenSegment.new()
	led.name = node_name
	led.cells = _style.meter_cells
	led.digit_px = digit_px
	led.segment_px = segment_px
	led.slant = _style.meter_slant
	led.lit = _style.meter_lit
	led.unlit = _style.meter_unlit
	led.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	return led


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


## A style number for the callout's language, Chinese first like
## `FareFace._say`: the Kai face sets larger than the Latin at every line.
func _sized(zh: int, en: int) -> int:
	return zh if _language == Locale.CHINESE else en


## Numerals with the housing's dark round them, for a readout with no panel.
func _outlined(label: Label) -> Label:
	label.add_theme_constant_override(&"outline_size", _style.timer_outline_px)
	label.add_theme_color_override(&"font_outline_color", _style.plate_field)
	return label


## A centred row of controls, `gap` px apart, inside `parent`.
static func _row(parent: Control, node_name: String, gap: int) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.name = node_name
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_theme_constant_override(&"separation", gap)
	parent.add_child(row)
	return row


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
##
## ⚠️ **In the minimap's strip it is the LETTERING that is cut, not the box**:
## the strip is the map's width whatever the name, so a name too long for it —
## `CENTRAL-WAN CHAI BYPASS TUNNEL` is 30 characters — is set smaller, each line
## on its own, and every other name is set at the style's size.
func _fit_plate() -> void:
	# Both homes set a name too long for the box smaller; the strip's margin is
	# the plate's vertical pad, because it has no chamfered ends to clear.
	var in_strip: bool = _minimap != null
	var pad: float = _style.plate_pad.y if in_strip else _style.plate_pad.x
	var room: float = _layout.street_plate.size.x - pad * 2.0
	StreetPlate.shrink_to(_plate_en, _style.plate_size_en, room)
	StreetPlate.shrink_to(_plate_zh, _style.plate_size_zh, room)
	if in_strip:
		return
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
	_update_tick(delta)
	# The map and the needle, every frame and off one look at the car: both are
	# motion, and a needle stepped at the numerals' 10 Hz ticks like a clock.
	# Each is a transform, so nothing is redrawn (`minimap.gd`, `speed_dial.gd`).
	var car: VehicleController = _vehicle()
	if car == null:
		return
	_dial.show_kph(car.speed_kph)
	if _minimap != null:
		var placed: Transform3D = car.global_transform
		_minimap.follow(placed.origin, -placed.basis.z)


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
	if not _plate_host.visible:
		_plate_host.visible = true
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
	if not is_instance_valid(vehicle):
		vehicle = null
	if vehicle != _followed:
		_followed = vehicle
		# ⚠️ A fresh car is not a continuation of the old one's velocity. Without
		# this the first sample after a respawn or a scene change differentiates
		# across the gap and pins the bar hard over for a filter time-constant.
		_last_speed_ms = 0.0 if vehicle == null else vehicle.speed_kph / 3.6
	return vehicle


# ------------------------------------------------------------------ fares ----


## Let go of the system this HUD was reading, if it is still there to let go of.
func _unfollow_fares() -> void:
	if not is_instance_valid(fares):
		return
	if fares.sampled.is_connected(_on_fare_sampled):
		fares.sampled.disconnect(_on_fare_sampled)
		fares.delivered.disconnect(_on_fare_delivered)
		fares.bailed.disconnect(_on_fare_bailed)
		fares.meter_changed.disconnect(_on_meter_changed)
		fares.skilled.disconnect(_on_fare_skilled)
		fares.practised.disconnect(_on_fare_practised)


## Read the new system: its pool onto the map, its samples into the face.
##
## ⚠️ **Signal-driven, never polled.** Under `--fares=off` the system frees
## itself in its own `_ready`, before `Main` hands it here, so a `_process`
## that reached into it would be reading a freed node by the second frame.
## Everything this reads from it is read inside one of its own signals, where
## it is alive by definition, or right here, where it still is.
func _follow_fares() -> void:
	_face = null
	if _meter_panel == null or not is_instance_valid(fares) or not fares.usable():
		_paint_fares()
		return
	_face = FareFace.new(ceili(_style.callout_hold_s * fares.sample_hz()), _language)
	fares.sampled.connect(_on_fare_sampled)
	fares.delivered.connect(_on_fare_delivered)
	fares.bailed.connect(_on_fare_bailed)
	fares.meter_changed.connect(_on_meter_changed)
	fares.skilled.connect(_on_fare_skilled)
	fares.practised.connect(_on_fare_practised)
	if _minimap != null:
		var points := PackedVector3Array()
		for stop: Fare.Stop in fares.pickups():
			points.append(stop.point)
		_minimap.set_pickups(points)
	_on_fare_sampled()


## The legal route to the destination onto the map (`P3-46`): the fare's own
## `route`, read here inside the sample it was written in; none with no
## target, before the hail, and where the car's edge reaches nothing.
##
## Walked and rebuilt only when it moved: the same edges from a start under
## `ROUTE_STEP_M` further along is the line already drawn, and a parked car's
## `Hit.t` jitters in its last bits every sample.
func _paint_route() -> void:
	var fare: Fare = null
	if _face.has_target and _face.target_is_destination and is_instance_valid(fares):
		fare = fares.fare
	if fare == null or fare.destination == null or fare.route == null or not fare.route.found:
		_route_edges = PackedInt32Array()
		_minimap.set_route(PackedVector2Array())
		return
	if fare.route.edges == _route_edges:
		var moved_m: float = (
			absf(fare.route_from_t - _route_from_t) * _graph.plan_length_of(_route_edges[0])
		)
		if moved_m < ROUTE_STEP_M:
			return
	_route_edges = fare.route.edges
	_route_from_t = fare.route_from_t
	_minimap.set_route(
		MinimapMesh.route_points(_graph, fare.route, fare.route_from_t, fare.destination.t)
	)


func _on_fare_delivered(fare: Fare) -> void:
	_face.on_ended(fare, true)
	# What was banked, meter and tip as one, in the gain's green.
	_flash(FareFace.flash(fare.banked_hkd), _style.accent)


## A unit began: the tick, in the chip's ink. The first is the flagfall.
func _on_meter_changed(_hkd: float, delta_hkd: float) -> void:
	if delta_hkd > 0.0:
		_flash(FareFace.flash(delta_hkd), _style.chip_ink)


## A skill paid (`P3-49`): the money and its name, in the gain's green, so a
## tip is seen being earned and not only counted at the door.
func _on_fare_skilled(_fare: Fare, award: Fare.Award) -> void:
	_flash(_face.award_text(award), _award_ink(award))


## A skill performed with no passenger aboard: its name alone, in the same
## ink, so a stunt can be practised between fares — nothing is paid.
func _on_fare_practised(award: Fare.Award) -> void:
	_flash(_face.practice_text(award), _award_ink(award))


func _award_ink(award: Fare.Award) -> Color:
	return _style.accent if award.hkd >= 0.0 else _style.accent_negative


## Show `text` under the clock and start it fading.
func _flash(text: String, ink: Color) -> void:
	_tick.text = text
	_tick.add_theme_color_override(&"font_color", ink)
	_tick.modulate = Color.WHITE
	_tick.visible = true
	_tick_s = _style.tick_fade_s


## Fade the tick out: alpha follows the time left, and the label hides at the
## end rather than sitting invisible in the tree.
func _update_tick(delta: float) -> void:
	if not _tick.visible:
		return
	_tick_s -= delta
	if _tick_s <= 0.0:
		_tick.visible = false
		return
	_tick.modulate = Color(
		1.0, 1.0, 1.0, clampf(_tick_s / maxf(_style.tick_fade_s, 0.001), 0.0, 1.0)
	)


func _on_fare_bailed(fare: Fare) -> void:
	_face.on_ended(fare, false)


## One sample of the loop, at its 5 Hz: the face decides and the panels are
## painted.
func _on_fare_sampled() -> void:
	var car: VehicleController = _vehicle()
	var nearest: Fare.Stop = null if car == null else fares.nearest_pending(car.global_position)
	_face.on_sampled(fares.state, fares.fare, nearest, _style.timer_warn_s, fares.earned_hkd)
	if _minimap != null and car != null:
		_minimap.withhold(fares.withheld_pickups(car.global_position))
	_paint_fares()


## The face onto the three panels and the map. Every write is guarded on what
## is already shown: `Label.text` is a reshape and `visible` a re-composite,
## and this runs for the whole session.
func _paint_fares() -> void:
	if _meter_panel == null:
		return
	if _face == null:
		_meter_panel.visible = false
		_timer_box.visible = false
		_callout_panel.visible = false
		_tick.visible = false
		if _minimap != null:
			_minimap.set_target(Vector3.ZERO, false)
			_minimap.set_route(PackedVector2Array())
			_minimap.set_beacon(Vector3.ZERO, false, _style.map_destination)
			_minimap.show_pending(false)
		return
	if not _meter_panel.visible:
		_meter_panel.visible = true
	_meter.text = _face.meter_text
	var tipping: bool = not _face.tip_text.is_empty()
	if _tip_row.visible != tipping:
		_tip_row.visible = tipping
	if tipping:
		_tip.text = _face.tip_text
		if _tip_caption.text != _face.tip_caption:
			_tip_caption.text = _face.tip_caption
	if _total.text != _face.total_text:
		_total.text = _face.total_text

	if _timer_box.visible != _face.show_timer:
		_timer_box.visible = _face.show_timer
	if _face.show_timer:
		if _timer_value.text != _face.timer_text:
			_timer_value.text = _face.timer_text
		var ink: Color = _style.meter_lit if _face.timer_urgent else _style.chip_ink
		if _timer_value.get_theme_color(&"font_color") != ink:
			_timer_value.add_theme_color_override(&"font_color", ink)

	var saying: bool = not _face.caption.is_empty()
	if _callout_panel.visible != saying:
		_callout_panel.visible = saying
	if saying:
		if _caption.text != _face.caption:
			_caption.text = _face.caption
		# Each line on its own guard: carrying, the road line changes every ten
		# metres and the place does not, and a refit reshapes the label.
		# Cut to the box, like the plate's lettering: a building's name can run
		# to forty characters, and the box is the worst case, not a suggestion.
		var room: float = _layout.callout.size.x - _style.plate_pad.x * 2.0
		var place: String = StreetPlate.substitute(_face.callout, _substitutions)
		if _callout.text != place:
			_callout.text = place
			StreetPlate.shrink_to(
				_callout, _sized(_style.callout_size_zh, _style.callout_size_en), room
			)
		var road: String = StreetPlate.substitute(_face.callout_sub, _substitutions)
		if _callout_sub.text != road:
			_callout_sub.text = road
			StreetPlate.shrink_to(
				_callout_sub, _sized(_style.callout_sub_size_zh, _style.callout_sub_size), room
			)

	if _minimap != null:
		_minimap.set_target(_face.target, _face.has_target and _face.target_is_destination)
		_paint_route()
		var beacon_ink: Color = (
			_style.map_destination if _face.target_is_destination else _style.map_pickup
		)
		_minimap.set_beacon(_face.target, _face.has_target, beacon_ink)
		_minimap.show_pending(not _face.target_is_destination)
