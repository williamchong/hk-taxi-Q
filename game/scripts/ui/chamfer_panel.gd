class_name ChamferPanel
extends Control
## A flat panel with cut corners — the HUD's one shape (`P3-24`).
##
## **The UI is flat-shaded too, and this is what says so.** `ART_DESIGN.md`'s
## direction is "low-poly, flat-shaded" with hard normals, and a `StyleBoxFlat`
## with a corner radius and a thin neutral keyline is operating-system chrome
## that sits on the frame like a dialog. Rounded corners and soft greys are the
## two things nothing else in this project has.
##
## So every panel here is a **polygon with its corners cut**, drawn in one flat
## fill with one hard keyline. It is the cheapest possible echo of the faceted
## geometry behind it, and it belongs to no other UI toolkit.
##
## ⚠️ **Not a `StyleBox`.** A chamfer is not expressible as a corner radius, and
## `StyleBoxFlat` has no polygon mode; going through the theme system would mean
## a texture or a nine-patch, and this bundle ships no UI textures for the same
## reason it ships almost none for the city.
##
## **Shape only.** A panel that also carries a reading is `AccentBar`, which
## extends this. The street plate and the three reserved slots want the shape
## and nothing else, and a widget carrying five speedometer properties that are
## inert on four of its five instances has stopped being about one thing.

## The corner cut, in pixels at the design resolution. One number for every
## corner and every panel — the shape is a rule, not a per-panel decision.
@export var chamfer_px: float:
	set(value):
		chamfer_px = value
		queue_redraw()

@export var fill: Color:
	set(value):
		fill = value
		queue_redraw()

## The keyline. Transparent for a panel that wants none.
@export var edge: Color:
	set(value):
		edge = value
		queue_redraw()

@export var edge_px: float:
	set(value):
		edge_px = value
		queue_redraw()

# The outline, kept between redraws. It is a pure function of the panel's size
# and its cut, while the speed chip redraws whenever the car's acceleration
# moves — so rebuilding an eight-point `PackedVector2Array` inside `_draw` was a
# heap allocation per frame for a shape that changes only on resize.
var _points: PackedVector2Array = PackedVector2Array()
var _points_for_box: Vector2 = Vector2.INF
var _points_for_cut: float = -1.0


func _ready() -> void:
	# Nothing here is interactive, and a Control over the game that swallows
	# clicks is how a HUD breaks the touch input it was supposed to be leaving
	# room for. Set here rather than at every call site so it cannot be
	# forgotten.
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _draw() -> void:
	var points: PackedVector2Array = outline()
	if fill.a > 0.0:
		draw_colored_polygon(points, fill)
	if edge.a > 0.0 and edge_px > 0.0:
		var closed: PackedVector2Array = points.duplicate()
		closed.append(points[0])
		draw_polyline(closed, edge, edge_px)


## The corner cut this panel can actually take.
##
## Clamped so a panel smaller than two chamfers degenerates to a rectangle
## rather than turning inside out. A slot can be resized by a container at any
## time and this must never draw a bowtie.
func cut() -> float:
	return minf(chamfer_px, minf(size.x, size.y) * 0.5)


## The eight corners, clockwise from the top-left cut, cached across redraws.
func outline() -> PackedVector2Array:
	var box: Vector2 = size
	var corner: float = cut()
	if box != _points_for_box or not is_equal_approx(corner, _points_for_cut):
		_points = _corners(box, corner)
		_points_for_box = box
		_points_for_cut = corner
	return _points


static func _corners(box: Vector2, corner: float) -> PackedVector2Array:
	return PackedVector2Array(
		[
			Vector2(corner, 0.0),
			Vector2(box.x - corner, 0.0),
			Vector2(box.x, corner),
			Vector2(box.x, box.y - corner),
			Vector2(box.x - corner, box.y),
			Vector2(corner, box.y),
			Vector2(0.0, box.y - corner),
			Vector2(0.0, corner),
		]
	)
