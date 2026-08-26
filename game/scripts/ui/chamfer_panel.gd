class_name ChamferPanel
extends Control
## A flat panel with cut corners — the HUD's one shape (`P3-24`).
##
## **The UI is flat-shaded too, and this is what says so.** `ART_DESIGN.md`'s
## direction is "low-poly, flat-shaded" with hard normals and no textures, and
## the first draft of this HUD ignored it: a `StyleBoxFlat` with a 4 px corner
## radius and a thin neutral keyline is operating-system chrome, and it sat on
## the frame like a dialog box that had wandered into the game. Rounded corners
## and soft greys are the two things nothing else in this project has.
##
## So every panel here is a **polygon with its corners cut**, drawn in one flat
## fill with one hard keyline. It is the cheapest possible echo of the faceted
## geometry behind it, it costs one `draw_colored_polygon` and one
## `draw_polyline`, and it belongs to no other UI toolkit.
##
## ⚠️ **Not a `StyleBox`.** A chamfer is not expressible as a corner radius, and
## `StyleBoxFlat` has no polygon mode; going through the theme system would mean
## a texture or nine-patch, and this bundle ships no UI textures for the same
## reason it ships almost none for the city.

## The corner cut, in pixels at the design resolution. One number for every
## corner and every panel — the shape is a rule, not a per-panel decision.
@export var chamfer_px: float = 14.0:
	set(value):
		chamfer_px = value
		queue_redraw()

@export var fill: Color = Color(0.16, 0.155, 0.145, 0.88):
	set(value):
		fill = value
		queue_redraw()

## The keyline. Transparent for a panel that wants none.
@export var edge: Color = Color(0.07, 0.07, 0.08, 1.0):
	set(value):
		edge = value
		queue_redraw()

@export var edge_px: float = 3.0:
	set(value):
		edge_px = value
		queue_redraw()

## A heavier bar along the bottom edge, between the two bottom cuts. This is
## where the accent colour lives — one saturated stripe per panel, which is what
## keeps the yellow to an accent rather than letting it become a field colour.
@export var accent: Color = Color(0, 0, 0, 0):
	set(value):
		accent = value
		queue_redraw()

@export var accent_px: float = 5.0:
	set(value):
		accent_px = value
		queue_redraw()


func _ready() -> void:
	# Nothing here is interactive, and a Control over the game that swallows
	# clicks is how a HUD breaks touch input it was supposed to be leaving room
	# for. Set here rather than at every call site so it cannot be forgotten.
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _draw() -> void:
	var box: Vector2 = size
	# Clamped so a panel smaller than two chamfers degenerates to a rectangle
	# rather than turning inside out. A HUD slot can be resized by a container
	# at any time and this must never draw a bowtie.
	var cut: float = minf(chamfer_px, minf(box.x, box.y) * 0.5)
	var points: PackedVector2Array = _outline(box, cut)

	if fill.a > 0.0:
		draw_colored_polygon(points, fill)
	if edge.a > 0.0 and edge_px > 0.0:
		var closed: PackedVector2Array = points.duplicate()
		closed.append(points[0])
		draw_polyline(closed, edge, edge_px)
	if accent.a > 0.0 and accent_px > 0.0:
		# Between the two bottom cuts, so the bar sits inside the shape rather
		# than running past its own corners.
		draw_line(
			Vector2(cut, box.y - accent_px * 0.5),
			Vector2(box.x - cut, box.y - accent_px * 0.5),
			accent,
			accent_px
		)


## The eight corners of a rectangle with every corner cut, clockwise from the
## top-left cut.
static func _outline(box: Vector2, cut: float) -> PackedVector2Array:
	return PackedVector2Array(
		[
			Vector2(cut, 0.0),
			Vector2(box.x - cut, 0.0),
			Vector2(box.x, cut),
			Vector2(box.x, box.y - cut),
			Vector2(box.x - cut, box.y),
			Vector2(cut, box.y),
			Vector2(0.0, box.y - cut),
			Vector2(0.0, cut),
		]
	)
