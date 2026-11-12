class_name LoadingCover
extends Control
## The loading screen over the menu's first seconds (`Q209`, the user's pick): a
## toy taxi idling on its springs over the cab's meter, the fare ticking up from
## the flag fall as the city arrives.
##
## It takes over from the boot splash, which is the same taxi standing still
## (`tools/make_splash.py`): both read `assets/authored/loading/taxi.json` and lay
## out against the screen's height from its centre, so the hand-over does not
## move a pixel of the taxi or the line. The meter is the cover's alone — while
## the splash is up the main thread is building the city and nothing can count.
##
## `ShaderWarmup` owns it and sets `progress`. The meter's cells read the
## progress itself; the fare is decoration on the same number, flag fall to
## `full_hkd`. Drawn, never a texture, like the guide's pictures: a few rounded
## polygons and circles, the bundled Kai, and the HUD's own `SevenSegment`.

const DRAWING_PATH: String = "res://assets/authored/loading/taxi.json"
## Points per rounded corner, as `tools/make_splash.py` builds them.
const CORNER_STEPS: int = 6
## What the meter's caption reads, left of the digits as on a cab's meter.
const CURRENCY: String = "HK$"

## How far loading has got, 0 to 1. It never goes back: a count that moves
## backwards reads as a fault, whatever the streamer is doing.
var progress: float = 0.0:
	set(value):
		progress = maxf(progress, clampf(value, 0.0, 1.0))
		_show_fare()

var _drawing: Dictionary = {}
var _style: HudStyle = null
var _font: Font = null
var _line: String = ""
var _flagfall_hkd: float = 0.0
var _meter: SevenSegment = null
var _box: StyleBoxFlat = null
## Stage units to canvas pixels: the screen's height over `stage_px`.
var _scale: float = 1.0
## The caption's size and the room it takes left of the digits, set by `_layout`.
var _currency_px: int = 1
var _currency_w: float = 0.0
var _time_s: float = 0.0


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_drawing = _load_drawing()
	_style = load(HudStyle.PATH) as HudStyle
	_font = StreetPlate.load_font_zh("loading")
	if _font == null:
		_font = ThemeDB.fallback_font
	var text: MenuText = MenuText.load_text()
	_line = "%s · %s" % [text.say("loading", "zh"), text.say("loading", "en")]
	var tariff := load(FareTariff.PATH) as FareTariff
	_flagfall_hkd = tariff.flagfall_hkd if tariff != null else 0.0
	if _drawing.is_empty() or _style == null:
		return
	var spec: Dictionary = _drawing["meter"]
	_box = StyleBoxFlat.new()
	_box.bg_color = Color.html(spec["fill"])
	_box.border_color = Color.html(spec["edge"])
	_meter = SevenSegment.new()
	_meter.name = "Fare"
	_meter.cells = int(spec["cells"])
	_meter.slant = _style.meter_slant
	_meter.lit = _style.meter_lit
	_meter.unlit = _style.meter_unlit
	add_child(_meter)
	resized.connect(_layout)
	_layout()
	_show_fare()


func _process(delta: float) -> void:
	_time_s += delta
	queue_redraw()


## The fare the meter shows at `progress`, in dollars to one place.
func fare_hkd() -> float:
	if _drawing.is_empty():
		return _flagfall_hkd
	var full: float = float(_drawing["meter"]["full_hkd"])
	return snappedf(lerpf(_flagfall_hkd, full, progress), 0.1)


## How many of the meter's cells are lit at `progress`.
func lit_cells() -> int:
	if _drawing.is_empty():
		return 0
	return roundi(float(_drawing["meter"]["bar_cells"]) * progress)


static func _load_drawing() -> Dictionary:
	var file := FileAccess.open(DRAWING_PATH, FileAccess.READ)
	if file == null:
		push_warning("LoadingCover: %s did not open; the cover stays plain" % DRAWING_PATH)
		return {}
	var parsed: Variant = JSON.parse_string(file.get_as_text())
	if not parsed is Dictionary:
		push_warning("LoadingCover: %s is not a JSON object" % DRAWING_PATH)
		return {}
	return parsed


func _layout() -> void:
	_scale = size.y / float(_drawing["stage_px"])
	var spec: Dictionary = _drawing["meter"]
	_box.set_corner_radius_all(roundi(float(spec["radius"]) * _scale))
	_box.set_border_width_all(maxi(1, roundi(float(spec["edge_px"]) * _scale)))
	_meter.digit_px = float(spec["digit_px"]) * _scale
	_meter.segment_px = float(spec["segment_px"]) * _scale
	_currency_px = maxi(1, roundi(float(spec["currency_px"]) * _scale))
	# A space's room after the caption, so it never touches the first digit.
	_currency_w = (
		_font.get_string_size(CURRENCY + " ", HORIZONTAL_ALIGNMENT_LEFT, -1, _currency_px).x
	)
	var digits: Vector2 = _meter.get_combined_minimum_size()
	# Nudged right of centre so the caption and the digits centre as one.
	var band_middle: float = float(spec["y"]) + float(spec["bar_y"]) * 0.5
	_meter.size = digits
	_meter.position = (
		size * 0.5 + Vector2((_currency_w - digits.x) * 0.5, band_middle * _scale - digits.y * 0.5)
	)


func _show_fare() -> void:
	if _meter != null:
		_meter.text = "%.1f" % fare_hkd()


func _draw() -> void:
	if _drawing.is_empty() or _style == null:
		return
	var idle: Dictionary = _drawing["idle"]
	var phase: float = fmod(_time_s / float(idle["loop_s"]), 1.0)
	var beat: float = TAU * float(idle["bounces"]) * phase
	var bob: float = float(idle["bounce_px"]) * absf(sin(beat))
	# Every term is at rest at time 0, as the still splash it takes over from is.
	var tilt: float = deg_to_rad(float(idle["rock_deg"]) * sin(beat))
	var squash: float = float(idle["squash"]) * maxf(0.0, -cos(2.0 * beat))
	var ground: float = float(_drawing["ground_y"])
	var half: float = float(_drawing["ground_half_px"])
	draw_line(
		_at(Vector2(-half, ground)),
		_at(Vector2(half, ground)),
		Color.html(_drawing["ground_colour"]),
		maxf(1.0, _scale)
	)
	_draw_exhaust(phase, ground)
	var body := Transform2D(tilt, Vector2(0.0, ground - float(_drawing["ride_px"]) - bob))
	body = body * Transform2D(Vector2.RIGHT, Vector2(0.0, 1.0 - squash), Vector2.ZERO)
	for shape: Dictionary in _drawing["body"]:
		var colour := Color.html(shape["colour"])
		if shape.has("rrect"):
			var corners: Array = shape["rrect"]
			var outline := PackedVector2Array()
			for point: Vector2 in _rounded_rect(corners, float(shape["radius"])):
				outline.append(_at(body * point))
			draw_colored_polygon(outline, colour)
		else:
			var anchor: Array = shape["at"]
			_text_top_centre(
				_at(body * Vector2(anchor[0], anchor[1])), shape["text"], float(shape["px"]), colour
			)
	var wheels: Dictionary = _drawing["wheels"]
	var radius: float = float(wheels["radius"])
	for x: float in wheels["x"]:
		var hub: Vector2 = _at(Vector2(x, ground - radius))
		draw_circle(hub, radius * _scale, Color.html(wheels["tyre"]))
		draw_circle(hub, float(wheels["hub_radius"]) * _scale, Color.html(wheels["hub"]))
	var line: Dictionary = _drawing["line"]
	_text_top_centre(
		_at(Vector2(0.0, float(line["y"]))), _line, float(line["px"]), Color.html(line["colour"])
	)
	_draw_meter()


func _draw_exhaust(phase: float, ground: float) -> void:
	var puffs: Dictionary = _drawing["exhaust"]
	var count: int = int(puffs["count"])
	var from: Vector2 = Vector2(puffs["from"][0], puffs["from"][1] + ground)
	var drift: Vector2 = Vector2(puffs["drift"][0], puffs["drift"][1])
	var colour := Color.html(puffs["colour"])
	for k: int in count:
		var age: float = fmod(phase + float(k) / count, 1.0)
		colour.a = float(puffs["alpha"]) * (1.0 - age)
		var r: float = lerpf(float(puffs["radius"][0]), float(puffs["radius"][1]), age)
		draw_circle(_at(from + drift * age), r * _scale, colour)


func _draw_meter() -> void:
	var spec: Dictionary = _drawing["meter"]
	var box_size := Vector2(spec["box"][0], spec["box"][1])
	var top: float = float(spec["y"])
	var corner: Vector2 = _at(Vector2(-box_size.x * 0.5, top))
	draw_style_box(_box, Rect2(corner, box_size * _scale))
	var foot: float = _meter.position.y + _meter.size.y
	draw_string(
		_font,
		Vector2(_meter.position.x - _currency_w, foot),
		CURRENCY,
		HORIZONTAL_ALIGNMENT_LEFT,
		-1,
		_currency_px,
		Color.html(spec["currency_colour"])
	)
	var cells: int = int(spec["bar_cells"])
	var cell := Vector2(spec["bar_cell"][0], spec["bar_cell"][1])
	var gap: float = float(spec["bar_gap"])
	var run: float = cells * cell.x + (cells - 1) * gap
	var lit: int = lit_cells()
	for i: int in cells:
		var origin := Vector2(-run * 0.5 + i * (cell.x + gap), top + float(spec["bar_y"]))
		draw_rect(
			Rect2(_at(origin), cell * _scale), _style.meter_lit if i < lit else _style.meter_unlit
		)


## A stage point to canvas pixels: from the screen's centre, scaled by its height.
func _at(stage: Vector2) -> Vector2:
	return size * 0.5 + stage * _scale


func _text_top_centre(top: Vector2, text: String, px_stage: float, colour: Color) -> void:
	var px: int = maxi(1, roundi(px_stage * _scale))
	var baseline := Vector2(top.x - size.x * 0.5, top.y + _font.get_ascent(px))
	draw_string(_font, baseline, text, HORIZONTAL_ALIGNMENT_CENTER, size.x, px, colour)


static func _rounded_rect(corners: Array, radius: float) -> PackedVector2Array:
	var x0: float = corners[0]
	var y0: float = corners[1]
	var x1: float = corners[2]
	var y1: float = corners[3]
	var points := PackedVector2Array()
	var centres: Array[Vector3] = [
		Vector3(x1 - radius, y0 + radius, -90.0),
		Vector3(x1 - radius, y1 - radius, 0.0),
		Vector3(x0 + radius, y1 - radius, 90.0),
		Vector3(x0 + radius, y0 + radius, 180.0),
	]
	for centre: Vector3 in centres:
		for step: int in CORNER_STEPS + 1:
			var angle: float = deg_to_rad(centre.z + 90.0 * step / CORNER_STEPS)
			points.append(Vector2(centre.x, centre.y) + Vector2(cos(angle), sin(angle)) * radius)
	return points
