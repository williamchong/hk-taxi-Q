class_name ScopeDisc
extends Control
## The minimap's round field (`Q163`): a disc in `fill` whose outer `fade_px`
## falls to nothing, and an optional ring in `edge` at the rim.
##
## **The fade is the clip.** `minimap.gd` sets `clip_children` on this, which
## masks the roads by the alpha drawn here, so the map dissolves into the frame
## at its edge the way a head-up scope does rather than stopping at a line.
## `fill` itself stays opaque (`verify_hud`'s `map:` assertions); only the rim's
## vertex alpha goes to zero.
##
## The disc is centred in `room` — the map's own slot, not the strip below it —
## at the largest radius that fits.

## Segments round the rim: at a 140 px radius a side is under 7 px.
const SEGMENTS: int = 64

@export var fill: Color:
	set(value):
		fill = value
		queue_redraw()
@export var edge: Color:
	set(value):
		edge = value
		queue_redraw()
@export var edge_px: float:
	set(value):
		edge_px = value
		queue_redraw()
@export var fade_px: float:
	set(value):
		fade_px = value
		queue_redraw()
## The rect the disc fills, in this node's own pixels.
@export var room: Rect2:
	set(value):
		room = value
		queue_redraw()

## The fade, kept: a mesh made inside `_draw` is freed when it returns, before
## the frame that draws it.
var _fade: ArrayMesh = null


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE


## The disc's centre and radius, as `(x, y, r)`.
func circle() -> Vector3:
	return circle_in(room)


static func circle_in(box: Rect2) -> Vector3:
	var centre: Vector2 = box.get_center()
	return Vector3(centre.x, centre.y, minf(box.size.x, box.size.y) * 0.5)


func _draw() -> void:
	var placed: Vector3 = circle()
	var centre := Vector2(placed.x, placed.y)
	var radius: float = placed.z
	if radius <= 0.0:
		return
	if fill.a > 0.0:
		# One mesh, one draw: the core as a fan in `fill`, then the fade as a
		# strip of quads, opaque on its inside edge.
		var inner: float = maxf(radius - fade_px, 0.0)
		var clear := Color(fill, 0.0)
		var points := PackedVector2Array()
		var colours := PackedColorArray()
		for index: int in SEGMENTS:
			var a := Vector2.from_angle(TAU * index / SEGMENTS)
			var b := Vector2.from_angle(TAU * (index + 1) / SEGMENTS)
			var core: Array[Vector2] = [centre, centre + a * inner, centre + b * inner]
			var rim: Array[Vector2] = [
				centre + a * inner,
				centre + a * radius,
				centre + b * radius,
				centre + a * inner,
				centre + b * radius,
				centre + b * inner,
			]
			points.append_array(PackedVector2Array(core + rim))
			colours.append_array([fill, fill, fill, fill, clear, clear, fill, clear, fill])
		_fade = CanvasMesh.of(points, colours)
		draw_mesh(_fade, null)
	if edge.a > 0.0 and edge_px > 0.0:
		draw_arc(centre, radius - fade_px * 0.5, 0.0, TAU, SEGMENTS, edge, edge_px, true)
