class_name AccentBar
extends ChamferPanel
## A chamfered panel that also carries one signed reading (`P3-24`).
##
## The speed chip. `ChamferPanel` draws the shape; this adds the bar along its
## bottom edge, between the two bottom cuts so neither runs past the shape's own
## corners.
##
## **Centre-origin, and two hues rather than one.** The quantity is signed and a
## driver reads *gaining or losing* before they read how much, so the bar grows
## out from the middle of its bed and changes colour rather than only length.
## Which hue means which is `HudStyle`'s to say and `verify_hud.gd`'s to enforce.

## The bar's colour above zero.
@export var accent: Color:
	set(value):
		accent = value
		queue_redraw()

## And below it. A second hue rather than a shorter bar: losing speed and
## gaining it are different events, not two ends of one quantity to a driver.
@export var accent_negative: Color:
	set(value):
		accent_negative = value
		queue_redraw()

## The unlit bed the bar runs in. Without it a reading of zero is
## indistinguishable from a panel that has stopped drawing.
@export var accent_track: Color:
	set(value):
		accent_track = value
		queue_redraw()

## The reading, -1.0 to 1.0.
@export var accent_fill: float:
	set(value):
		accent_fill = clampf(value, -1.0, 1.0)
		queue_redraw()

@export var accent_px: float:
	set(value):
		accent_px = value
		queue_redraw()


## Where the bar starts and ends along its bed, for a reading of `fill`.
##
## ⚠️ **Pure, and static, so it can be graded.** The direction of a centre-origin
## bar is the one thing here that renders perfectly while being wrong — inverted,
## or clamped on one side only, it still sweeps convincingly — and a check that
## only reads `accent_fill` back out of its own setter is testing Godot's
## `clampf`. `verify_hud.gd` asserts on this instead, and `_draw` calls the same
## function, so the two cannot disagree (`Q72`'s rule about a check that cannot
## fail).
## ⚠️ `reading` and not `fill` — `ChamferPanel.fill` is the panel's colour, and
## the warnings sweep promotes shadowing to an error.
static func bar_span(left: float, right: float, reading: float) -> Vector2:
	var middle: float = (left + right) * 0.5
	var reach: float = (right - middle) if reading > 0.0 else (middle - left)
	return Vector2(middle, middle + reach * clampf(reading, -1.0, 1.0))


func _draw() -> void:
	super()
	if accent_px <= 0.0:
		return

	var corner: float = cut()
	var y: float = size.y - accent_px * 0.5
	if accent_track.a > 0.0:
		draw_line(Vector2(corner, y), Vector2(size.x - corner, y), accent_track, accent_px)
	if is_zero_approx(accent_fill):
		return

	var ink: Color = accent if accent_fill > 0.0 else accent_negative
	if ink.a <= 0.0:
		return
	var span: Vector2 = bar_span(corner, size.x - corner, accent_fill)
	draw_line(Vector2(span.x, y), Vector2(span.y, y), ink, accent_px)
