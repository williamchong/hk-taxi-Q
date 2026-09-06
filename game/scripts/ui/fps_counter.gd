extends Label
## Frame rate and average frame time, top right of the dev overlay.
##
## A child `DebugHud` builds, not an autoload (`Q119`). It was the second of
## four autoloads and the only one whose `_ready` reached into another — it
## asked `DebugHud` what to show, so the registration order in `project.godot`
## was load-bearing and an autoload listed later "did not exist yet". Built by
## the overlay it is a view of, it is told rather than asking, and the order is
## a fact about one script. It carries no reference to its owner at all: the
## owner styles it and calls `show_stats`.
##
## Frame time is averaged from real deltas rather than derived from the rounded
## FPS integer — 60 and 60.9 fps both round to "16.7 ms" otherwise, which is
## exactly the resolution needed to spot a hitch.
##
## Processing stops whenever the label is hidden rather than the node being
## freed: a release build must not pay for a per-frame overlay against a <150
## draw call budget.

## Thresholds come from the 60fps mobile target in docs/ARCHITECTURE.md.
const WARN_FPS: float = 55.0
const BAD_FPS: float = 45.0
const UPDATE_INTERVAL_S: float = 0.25

var _accum_s: float = 0.0
var _frames: int = 0
## White to start with, which is what the owner's `style_label` sets. `_process`
## overrides it from there when the band changes.
var _colour: Color = Color.WHITE


func _ready() -> void:
	# Top right, opposite the overlay's top-left stack, so the two never fight
	# for a corner. The box is wider than the 152 px that held this text at the
	# default 16 px font, with the margin to match the stat size. Right-anchored
	# and right-aligned, so the extra width costs nothing if it is not used.
	set_anchors_preset(Control.PRESET_TOP_RIGHT)
	offset_left = -260.0
	offset_top = 8.0
	offset_right = -16.0
	horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	show_stats(false)


## Stop counting when nothing is showing the count, and start again from a clean
## window when it comes back — an average spanning the time the overlay was
## hidden would report a hitch that was only the toggle.
func show_stats(showing: bool) -> void:
	visible = showing
	set_process(showing)
	_accum_s = 0.0
	_frames = 0


func _process(delta: float) -> void:
	_accum_s += delta
	_frames += 1
	if _accum_s < UPDATE_INTERVAL_S:
		return

	var frame_ms: float = (_accum_s / float(_frames)) * 1000.0
	var fps: float = 1000.0 / frame_ms
	text = "%.0f fps\n%.1f ms" % [fps, frame_ms]

	# Overriding a theme colour dirties the font and forces a reshape, so only
	# do it when the band actually changes.
	var colour: Color = _colour_for(fps)
	if colour != _colour:
		_colour = colour
		add_theme_color_override(&"font_color", colour)

	_accum_s = 0.0
	_frames = 0


func _colour_for(fps: float) -> Color:
	if fps >= WARN_FPS:
		return Color.WHITE
	if fps >= BAD_FPS:
		return Color.YELLOW
	return Color.RED
