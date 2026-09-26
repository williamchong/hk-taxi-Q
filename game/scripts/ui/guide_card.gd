class_name GuideCard
extends Control
## One step's picture in the start menu's guide (`P6-1`, the user's ask:
## "a simple guide with image steps"): drawn, never a texture.
##
## Drawn because the bundle ships no UI textures (`chamfer_panel.gd`) and a
## screenshot of the city could not be committed as one — the generated data
## is never committed (hard rule 7), and a render of it is that data in
## another form. Each picture is a few flat polygons in the HUD's own palette
## (`HudStyle`), which is the art direction anyway: flat-shaded, hard edges,
## no radius but the sign's — the wrong-way step reuses `NoEntryIcon`, the
## sign the city actually draws.
##
## `kind` names the picture; `KINDS` is the closed set `verify_menu.gd` holds
## `menu_text.json`'s steps to, so a step naming a picture that does not exist
## fails the check rather than drawing an empty card.

const KINDS: PackedStringArray = ["drive", "pickup", "deliver", "skills", "wrong_way"]

## The stroke of every outline, in design pixels.
const STROKE: float = 3.0

var kind: String = "drive"
var style: HudStyle = null
## The wrong-way step's sign, a child because the sign draws itself.
var _sign: NoEntryIcon = null


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	if kind == "wrong_way" and style != null:
		_sign = NoEntryIcon.styled(style, "Sign")
		_sign.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(_sign)
	resized.connect(_place_sign)
	_place_sign()


func _place_sign() -> void:
	if _sign == null:
		return
	var side: float = minf(size.x, size.y) * 0.6
	_sign.position = Vector2(size.x * 0.62 - side * 0.5, (size.y - side) * 0.5)
	_sign.size = Vector2(side, side)


func _draw() -> void:
	if style == null:
		return
	match kind:
		"drive":
			_draw_drive()
		"pickup":
			_draw_pickup()
		"deliver":
			_draw_deliver()
		"skills":
			_draw_skills()
		"wrong_way":
			_draw_wrong_way()


# -------------------------------------------------------------- pictures ----


## Two thumbs: the left steers, the right is one axis — up to go, down to
## brake — with the keys over them for a desk.
func _draw_drive() -> void:
	var pad := Vector2(size.x * 0.34, size.y * 0.42)
	var left := Rect2(Vector2(size.x * 0.08, size.y * 0.5), pad)
	var right := Rect2(Vector2(size.x * 0.58, size.y * 0.5), pad)
	for rect: Rect2 in [left, right]:
		draw_rect(rect, style.accent_track, true)
		draw_rect(rect, style.plate_edge, false, STROKE)
	var ink: Color = style.plate_ink
	var c: Vector2 = left.get_center()
	_arrow(c + Vector2(-pad.x * 0.3, 0.0), Vector2.LEFT, pad.y * 0.28, ink)
	_arrow(c + Vector2(pad.x * 0.3, 0.0), Vector2.RIGHT, pad.y * 0.28, ink)
	c = right.get_center()
	_arrow(c + Vector2(0.0, -pad.y * 0.24), Vector2.UP, pad.y * 0.26, style.accent)
	_arrow(c + Vector2(0.0, pad.y * 0.24), Vector2.DOWN, pad.y * 0.26, style.accent_negative)
	_caps("A  D", Vector2(left.position.x, size.y * 0.16), pad.x)
	_caps("W  S", Vector2(right.position.x, size.y * 0.16), pad.x)


## A customer waits in a ring on the road; the taxi pulls up beside it.
func _draw_pickup() -> void:
	_road()
	var ring := Vector2(size.x * 0.68, size.y * 0.55)
	draw_arc(ring, size.y * 0.2, 0.0, TAU, 48, style.map_pickup, STROKE * 1.5, true)
	_person(ring, size.y * 0.22, style.plate_ink)
	_taxi(Vector2(size.x * 0.3, size.y * 0.55), size.x * 0.28)


## The route to the pin, with the clock running.
func _draw_deliver() -> void:
	_road()
	var from := Vector2(size.x * 0.18, size.y * 0.62)
	var pin := Vector2(size.x * 0.8, size.y * 0.42)
	var route := PackedVector2Array(
		[from, Vector2(size.x * 0.45, size.y * 0.62), Vector2(size.x * 0.55, size.y * 0.42), pin]
	)
	draw_polyline(route, style.map_route, STROKE * 1.5, true)
	_taxi(from, size.x * 0.2)
	var head: float = size.y * 0.09
	draw_circle(pin - Vector2(0.0, head * 1.6), head, style.map_destination, true, -1.0, true)
	draw_colored_polygon(
		PackedVector2Array(
			[pin, pin + Vector2(-head * 0.8, -head * 1.2), pin + Vector2(head * 0.8, -head * 1.2)]
		),
		style.map_destination
	)
	_caps("60", Vector2(size.x * 0.66, size.y * 0.72), size.x * 0.28)


## Three ways the tip grows: a slide, a fast run, an early arrival.
func _draw_skills() -> void:
	var third: float = size.x / 3.0
	var mid: float = size.y * 0.42
	# Drift: two tyre arcs.
	var drift := Vector2(third * 0.5, mid)
	for offset: float in [-0.12, 0.12]:
		draw_arc(
			drift + Vector2(size.x * offset, 0.0),
			size.y * 0.22,
			PI * 1.15,
			PI * 1.85,
			24,
			style.plate_ink,
			STROKE,
			true
		)
	# Speed: three chevrons.
	var speed := Vector2(third * 1.5, mid)
	for step: int in 3:
		_arrow(
			speed + Vector2((step - 1) * size.x * 0.07, 0.0),
			Vector2.RIGHT,
			size.y * 0.22,
			style.plate_ink
		)
	# Early: a clock with its hand short of the hour.
	var early := Vector2(third * 2.5, mid)
	var radius: float = size.y * 0.2
	draw_arc(early, radius, 0.0, TAU, 40, style.plate_ink, STROKE, true)
	draw_line(early, early + Vector2(0.0, -radius * 0.8), style.plate_ink, STROKE, true)
	draw_line(early, early + Vector2(radius * 0.55, -radius * 0.3), style.plate_ink, STROKE, true)
	for column: int in 3:
		_caps("+HK$", Vector2(third * column, size.y * 0.72), third, style.accent)


## The road runs one way; the sign says which.
func _draw_wrong_way() -> void:
	_road()
	_arrow(Vector2(size.x * 0.24, size.y * 0.55), Vector2.LEFT, size.y * 0.3, style.plate_ink)


# --------------------------------------------------------------- strokes ----


func _road() -> void:
	var band := Rect2(0.0, size.y * 0.32, size.x, size.y * 0.46)
	draw_rect(band, style.map_road, true)
	var dash: float = size.x * 0.08
	var x: float = dash * 0.5
	while x < size.x:
		draw_line(
			Vector2(x, band.get_center().y),
			Vector2(minf(x + dash, size.x), band.get_center().y),
			style.map_road_main,
			STROKE * 0.7
		)
		x += dash * 2.0


## The taxi from above: the red body and the white roof sign.
func _taxi(at: Vector2, length: float) -> void:
	var body := Rect2(at - Vector2(length * 0.5, length * 0.24), Vector2(length, length * 0.48))
	draw_rect(body, style.map_marker, true)
	var sign := Rect2(
		at - Vector2(length * 0.08, length * 0.08), Vector2(length * 0.16, length * 0.16)
	)
	draw_rect(sign, style.map_marker_edge, true)


func _person(at: Vector2, height: float, ink: Color) -> void:
	var head: float = height * 0.18
	draw_circle(at + Vector2(0.0, -height * 0.32), head, ink, true, -1.0, true)
	draw_rect(
		Rect2(at + Vector2(-height * 0.14, -height * 0.1), Vector2(height * 0.28, height * 0.42)),
		ink,
		true
	)


## A solid arrowhead pointing `along`, `length` from base to tip, centred.
func _arrow(at: Vector2, along: Vector2, length: float, ink: Color) -> void:
	var across: Vector2 = along.orthogonal()
	var tip: Vector2 = at + along * length * 0.5
	var base: Vector2 = at - along * length * 0.5
	draw_colored_polygon(
		PackedVector2Array([tip, base + across * length * 0.55, base - across * length * 0.55]), ink
	)


## Lettering in the theme's face, centred in a `width` at `at`.
func _caps(text: String, at: Vector2, width: float, ink: Color = Color.TRANSPARENT) -> void:
	var colour: Color = style.chip_muted if ink == Color.TRANSPARENT else ink
	var px: int = roundi(size.y * 0.14)
	draw_string(
		get_theme_default_font(),
		at + Vector2(0.0, px),
		text,
		HORIZONTAL_ALIGNMENT_CENTER,
		width,
		px,
		colour
	)
