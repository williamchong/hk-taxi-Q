class_name HeadUpFrame
extends Control
## The frame every bare readout hangs off (`Q163`): a vignette along the top and
## bottom edges and an L-bracket in each corner.
##
## **What makes four floating readouts one display.** With the housings gone the
## clock, the callout, the speed and the map had nothing in common but a font;
## the brackets say "this is one screen of glass", and the vignette is what the
## bare lettering reads against when the road behind it is white.
##
## One node and ONE draw: the bands and the brackets are a single
## vertex-coloured mesh, built on a resize and kept, with no texture (the
## bundle ships no UI ones). Drawn as polygons and polylines it was six calls.

var style: HudStyle = null
## Whether the vignette draws. The menu turns it off: its backdrop shades the
## text already, and its frame draws OVER the pages so the brackets show.
var shaded: bool = true

## Kept: a mesh made inside `_draw` is freed when it returns, before the frame
## that draws it.
var _mesh: ArrayMesh = null


## The frame in `style`, full-rect; `shaded` false leaves the vignette off.
static func styled(hud_style: HudStyle, with_vignette: bool = true) -> HeadUpFrame:
	var frame := HeadUpFrame.new()
	frame.name = "Frame"
	frame.style = hud_style
	frame.shaded = with_vignette
	frame.set_anchors_preset(Control.PRESET_FULL_RECT)
	return frame


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	resized.connect(queue_redraw)


func _draw() -> void:
	if style == null:
		return
	var points := PackedVector2Array()
	var colours := PackedColorArray()
	var reach: float = size.y * style.vignette_share
	if shaded and style.vignette.a > 0.0 and reach > 0.0:
		var clear := Color(style.vignette, 0.0)
		_quad(points, colours, Rect2(0.0, 0.0, size.x, reach), style.vignette, clear)
		_quad(points, colours, Rect2(0.0, size.y - reach, size.x, reach), clear, style.vignette)
	if style.frame_ink.a > 0.0 and style.frame_px > 0.0:
		var half: float = style.frame_px * 0.5
		for corner: PackedVector2Array in brackets(size, style.frame_inset_px, style.frame_arm_px):
			# Each arm a stroke-wide box, run half a stroke past the corner so the
			# two arms close the L without a notch.
			for arm: Vector2 in [corner[0], corner[2]]:
				var box := Rect2(corner[1], Vector2.ZERO).expand(arm).grow(half)
				_quad(points, colours, box, style.frame_ink, style.frame_ink)
	if points.is_empty():
		return
	_mesh = CanvasMesh.of(points, colours)
	draw_mesh(_mesh, null)


## `box` as two triangles, `upper` along its top edge and `lower` its bottom.
static func _quad(
	points: PackedVector2Array, colours: PackedColorArray, box: Rect2, upper: Color, lower: Color
) -> void:
	var top_right := Vector2(box.end.x, box.position.y)
	var bottom_left := Vector2(box.position.x, box.end.y)
	points.append_array([box.position, top_right, box.end, box.position, box.end, bottom_left])
	colours.append_array([upper, upper, lower, upper, lower, lower])


## The four brackets in `box`, each three points — arm, corner, arm — `inset`
## in from the edges with arms `arm` long. Clockwise from the top-left.
static func brackets(box: Vector2, inset: float, arm: float) -> Array[PackedVector2Array]:
	var corners: Array[PackedVector2Array] = []
	for at: Vector2 in [Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)]:
		var point := Vector2(lerpf(inset, box.x - inset, at.x), lerpf(inset, box.y - inset, at.y))
		var inward := Vector2(1.0 - at.x * 2.0, 1.0 - at.y * 2.0)
		var down := Vector2(0.0, inward.y * arm)
		var across := Vector2(inward.x * arm, 0.0)
		corners.append(PackedVector2Array([point + down, point, point + across]))
	return corners
