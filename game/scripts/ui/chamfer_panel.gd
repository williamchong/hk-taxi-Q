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
##
## ⚠️ **It carries a reading, and it did not always.** For one build this was a
## full-width stripe that never moved: an indicator on an instrument panel that
## indicated nothing, in a project whose whole discipline is that a thing on
## screen should be answerable for. It is now driven by `accent_fill`.
@export var accent: Color = Color(0, 0, 0, 0):
	set(value):
		accent = value
		queue_redraw()

## The colour the bar takes below zero. A second hue rather than a shorter bar,
## because losing speed and gaining it are different events and not two ends of
## one quantity to a driver.
@export var accent_negative: Color = Color(0, 0, 0, 0):
	set(value):
		accent_negative = value
		queue_redraw()

## The unlit bed the bar runs in. Without it a reading of zero is indis-
## tinguishable from a panel that has stopped drawing.
@export var accent_track: Color = Color(0, 0, 0, 0):
	set(value):
		accent_track = value
		queue_redraw()

## The reading, -1.0 to 1.0, drawn out from the centre of the bed. Centre-origin
## because the quantity is signed and a driver reads "gaining or losing" before
## they read how much.
@export var accent_fill: float = 0.0:
	set(value):
		accent_fill = clampf(value, -1.0, 1.0)
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
	if accent_px > 0.0:
		_draw_bar(box, cut)


## The bed, and the reading in it. Between the two bottom cuts, so neither runs
## past the shape's own corners.
func _draw_bar(box: Vector2, cut: float) -> void:
	var y: float = box.y - accent_px * 0.5
	var left: float = cut
	var right: float = box.x - cut
	var middle: float = (left + right) * 0.5

	if accent_track.a > 0.0:
		draw_line(Vector2(left, y), Vector2(right, y), accent_track, accent_px)
	if is_zero_approx(accent_fill):
		return

	var reach: float = (right - middle) if accent_fill > 0.0 else (middle - left)
	var ink: Color = accent if accent_fill > 0.0 else accent_negative
	if ink.a <= 0.0:
		return
	draw_line(Vector2(middle, y), Vector2(middle + reach * accent_fill, y), ink, accent_px)


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
