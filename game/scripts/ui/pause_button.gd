class_name PauseButton
extends Button
## The drive's pause (`P6-1`, `Q165`, the user's ask): two bars on the glass,
## the HUD's one control that takes a tap, since a phone has no Esc.
##
## Drawn, not a glyph from the font: the Kai has no ⏸ and a fallback face would
## set it at its own weight. Bare like every readout since `Q163` — the bars in
## the plate's ink over the float's drop shadow, lit in the accent while the
## pointer is on them, as the menu's choices are.
##
## ⚠️ **`FOCUS_NONE`, and that is load-bearing.** A focused button takes
## `ui_accept`, and Space is the handbrake: a pause that held the focus would open
## on the first slide.

## Each bar's width, and the gap between them, as a share of the side.
const BAR_SHARE: float = 0.16
const GAP_SHARE: float = 0.14
## The bars' height as a share of the side.
const HEIGHT_SHARE: float = 0.5

var style: HudStyle = null


func _ready() -> void:
	flat = true
	focus_mode = Control.FOCUS_NONE
	mouse_filter = Control.MOUSE_FILTER_STOP
	var empty := StyleBoxEmpty.new()
	for state: StringName in [&"normal", &"hover", &"pressed", &"hover_pressed", &"disabled"]:
		add_theme_stylebox_override(state, empty)
	mouse_entered.connect(queue_redraw)
	mouse_exited.connect(queue_redraw)


func _draw() -> void:
	if style == null:
		return
	var side: float = minf(size.x, size.y)
	var bar := Vector2(side * BAR_SHARE, side * HEIGHT_SHARE)
	var gap: float = side * GAP_SHARE
	var left := Vector2((size.x - bar.x * 2.0 - gap) * 0.5, (size.y - bar.y) * 0.5)
	var drop := Vector2.ONE * style.float_shadow_drop_px
	var ink: Color = style.accent if is_hovered() else style.plate_ink
	for offset: Vector2 in [Vector2.ZERO, Vector2(bar.x + gap, 0.0)]:
		draw_rect(Rect2(left + offset + drop, bar), style.float_shadow)
		draw_rect(Rect2(left + offset, bar), ink)
