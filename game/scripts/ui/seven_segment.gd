class_name SevenSegment
extends Control
## LED numerals, as a Hong Kong taxi meter draws them (`Q139`).
##
## `ART_DESIGN.md` names the HUD's language as road signage and the 的士咪錶; this
## is the meter's face, and it is for the FARE: a 咪錶 is a black housing with
## red seven-segment digits whose unlit segments stay faintly visible, and both
## halves of that are what make it read as a meter rather than as a red font.
##
## It was built for the speed, and the user pointed out that speed was never
## on a meter — that is the dashboard's (`speed_dial.gd`). `P3-5a` gave it the
## fare, in dollars to one place, which is what the decimal point is for.
##
## **Polygons, not a typeface**: a seven-segment face would be a fifth licence
## for ten glyphs (`Q79` counts four), and a cut hexagon a segment is already
## this HUD's one shape.
##
## 🔴 **One mesh, one draw call.** Lit and unlit, a display is 21 segments a
## three-digit readout, and a `draw_colored_polygon` each would be 21 canvas
## commands that do not batch — the mistake `minimap_mesh.gd` records making
## first. The mesh is rebuilt only when the text changes, which for the speed is
## at most ten times a second.

## Which segments a character lights, as bits a..g from the LSB:
## a top, b upper right, c lower right, d bottom, e lower left, f upper left,
## g middle. `r` is how a meter spells reverse; anything unlisted lights nothing.
## A `.` is not a glyph — it marks the cell before it (`cells_of`).
const GLYPHS: Dictionary[String, int] = {
	"0": 0b0111111,
	"1": 0b0000110,
	"2": 0b1011011,
	"3": 0b1001111,
	"4": 0b1100110,
	"5": 0b1101101,
	"6": 0b1111101,
	"7": 0b0000111,
	"8": 0b1111111,
	"9": 0b1101111,
	"r": 0b1010000,
	"-": 0b1000000,
	" ": 0b0000000,
}

## A digit's width and the gap to the next, as shares of its height.
const CELL_ASPECT: float = 0.56
const CELL_GAP: float = 0.2

## How many cells are drawn, lit or not. A meter's unlit digits are part of its
## face, and a fixed count keeps the numerals from walking as the speed grows.
@export var cells: int = 3:
	set(value):
		cells = value
		_rebuild()

@export var text: String = "":
	set(value):
		if value == text:
			return
		text = value
		_rebuild()

## A digit's height, in design pixels.
@export var digit_px: float:
	set(value):
		digit_px = value
		_rebuild()

## A segment's thickness, in design pixels.
@export var segment_px: float:
	set(value):
		segment_px = value
		_rebuild()

## How far the top of a digit leans right of its foot, as a share of its height.
@export var slant: float:
	set(value):
		slant = value
		_rebuild()

@export var lit: Color:
	set(value):
		lit = value
		_rebuild()

@export var unlit: Color:
	set(value):
		unlit = value
		_rebuild()

var _mesh: ArrayMesh = null


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _get_minimum_size() -> Vector2:
	return display_size(cells, digit_px, slant)


func _draw() -> void:
	if _mesh != null:
		# Centred in whatever box the container gave it.
		draw_mesh(_mesh, null, Transform2D(0.0, (size - _get_minimum_size()) * 0.5))


func _rebuild() -> void:
	_mesh = build(text, cells, digit_px, segment_px, slant, lit, unlit)
	update_minimum_size()
	queue_redraw()


## The box `cells` digits take, lean included.
static func display_size(count: int, height: float, lean: float) -> Vector2:
	var cell: float = height * CELL_ASPECT
	var gap: float = height * CELL_GAP
	return Vector2(count * cell + maxi(count - 1, 0) * gap + absf(lean) * height, height)


## The segments `character` lights. Nothing, for a character no meter can show.
static func segments_of(character: String) -> int:
	return GLYPHS.get(character, 0)


## `value` as the cells a display shows: a `.` is not a cell but a mark on the
## cell before it, so "29.0" is four cells with the second one dotted. A dot
## with no cell before it lights nothing. Right-aligned in `count` cells, the
## way a meter fills from the right.
static func cells_of(value: String, count: int) -> Array[Array]:
	var shown: Array[Array] = []
	for character: String in value:
		if character == "." and not shown.is_empty():
			shown[shown.size() - 1][1] = true
		elif character != ".":
			shown.append([character, false])
	while shown.size() > count:
		shown.pop_front()
	while shown.size() < count:
		shown.push_front([" ", false])
	return shown


## The display as one mesh: `value` right-aligned in `count` cells, every
## segment drawn, lit ones in `on` and the rest in `off`. Null with no size.
##
## ⚠️ The dots come AFTER every cell's segments, so a reader walking the mesh
## in strides of one segment (`verify_hud.gd`) sees the cells first and the
## dots as a tail — a dot drawn between two cells' segments would shift every
## cell after it.
static func build(
	value: String, count: int, height: float, thick: float, lean: float, on: Color, off: Color
) -> ArrayMesh:
	if count <= 0 or height <= 0.0 or thick <= 0.0:
		return null
	var shown: Array[Array] = cells_of(value, count)
	var vertices := PackedVector2Array()
	var colours := PackedColorArray()
	var dots := PackedVector2Array()
	var cell: float = height * CELL_ASPECT
	for index: int in count:
		var mask: int = segments_of(shown[index][0])
		var left: float = index * (cell + height * CELL_GAP)
		for segment: int in 7:
			var ink: Color = on if mask & (1 << segment) else off
			for point: Vector2 in _segment(segment, cell, height, thick):
				# The lean is about the FOOT, so the display's left edge stays put.
				vertices.append(Vector2(left + point.x + (height - point.y) * lean, point.y))
				colours.append(ink)
		if shown[index][1]:
			for point: Vector2 in _dot(cell, height, thick):
				dots.append(Vector2(left + point.x + (height - point.y) * lean, point.y))
	vertices.append_array(dots)
	for _dot_point: Vector2 in dots:
		colours.append(on)

	return CanvasMesh.of(vertices, colours)


## The decimal point: a square a segment thick at the cell's foot, in the gap
## to the next cell, as two triangles. Always lit — a meter has no ghost dot.
static func _dot(cell: float, height: float, thick: float) -> PackedVector2Array:
	var gap: float = thick * 0.12
	var left: float = cell + gap
	var top: float = height - thick
	return PackedVector2Array(
		[
			Vector2(left, top),
			Vector2(left + thick, top),
			Vector2(left + thick, height),
			Vector2(left, top),
			Vector2(left + thick, height),
			Vector2(left, height),
		]
	)


## One segment of an upright digit as four triangles: a bar with pointed ends,
## which is what lets two segments meet at a corner without overlapping.
static func _segment(segment: int, cell: float, height: float, thick: float) -> PackedVector2Array:
	var half: float = thick * 0.5
	# A hair of dark between neighbours, as the housing's mask leaves.
	var gap: float = thick * 0.12
	var middle: float = height * 0.5
	var from := Vector2.ZERO
	var to := Vector2.ZERO
	match segment:
		0:
			from = Vector2(half + gap, half)
			to = Vector2(cell - half - gap, half)
		1:
			from = Vector2(cell - half, half + gap)
			to = Vector2(cell - half, middle - gap)
		2:
			from = Vector2(cell - half, middle + gap)
			to = Vector2(cell - half, height - half - gap)
		3:
			from = Vector2(half + gap, height - half)
			to = Vector2(cell - half - gap, height - half)
		4:
			from = Vector2(half, middle + gap)
			to = Vector2(half, height - half - gap)
		5:
			from = Vector2(half, half + gap)
			to = Vector2(half, middle - gap)
		_:
			from = Vector2(half + gap, middle)
			to = Vector2(cell - half - gap, middle)
	var along: Vector2 = (to - from).normalized() * half
	var across: Vector2 = along.orthogonal()
	var hexagon: Array[Vector2] = [
		from,
		from + along + across,
		to - along + across,
		to,
		to - along - across,
		from + along - across,
	]
	var triangles := PackedVector2Array()
	for corner: int in range(1, 5):
		triangles.append_array([hexagon[0], hexagon[corner], hexagon[corner + 1]])
	return triangles
