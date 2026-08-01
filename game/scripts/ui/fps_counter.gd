extends CanvasLayer
## Performance overlay: frame rate and average frame time.
##
## Autoloaded, so it survives scene changes. Frame time is averaged from real
## deltas rather than derived from the rounded FPS integer — 60 and 60.9 fps
## both round to "16.7 ms" otherwise, which is exactly the resolution needed to
## spot a hitch.
##
## Shown only when `DebugHud` says so, which by default is never — the gate that
## used to live here moved there, because the counter is one of that HUD's views
## and two gates over one overlay is how they drift apart. `--fps` still turns it
## on, in a release build too; what changed is that it now brings the position
## block with it, since both are the HUD's `minimal` view.
##
## The old requirement is still met: a release build must not pay for a per-frame
## overlay against a <150 draw call budget, and processing stops whenever the
## label is hidden rather than the node being freed.

## Thresholds come from the 60fps mobile target in docs/ARCHITECTURE.md.
const WARN_FPS: float = 55.0
const BAD_FPS: float = 45.0
const UPDATE_INTERVAL_S: float = 0.25

var _label: Label
var _accum_s: float = 0.0
var _frames: int = 0
var _colour: Color = Color.WHITE


func _ready() -> void:
	layer = 128
	process_mode = Node.PROCESS_MODE_ALWAYS

	_label = Label.new()
	# Top right, opposite the HUD's top-left stack, so the two never fight for a
	# corner. The box is wider than the 152 px that held this text at the default
	# 16 px font, with the margin to match SIZE_STAT. Right-anchored and
	# right-aligned, so the extra width costs nothing if it is not used.
	_label.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	_label.offset_left = -260.0
	_label.offset_top = 8.0
	_label.offset_right = -16.0
	_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	# White to start with, which is what `_colour` holds and what `style_label`
	# sets. `_process` overrides it from there when the band changes.
	DebugHud.style_label(_label, DebugHud.SIZE_STAT)
	add_child(_label)

	DebugHud.view_changed.connect(_apply_view)
	_apply_view()


## Stop counting when nothing is showing the count, and start again from a clean
## window when it comes back — an average spanning the time the overlay was
## hidden would report a hitch that was only the toggle.
func _apply_view() -> void:
	var showing: bool = DebugHud.shows_stats()
	_label.visible = showing
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
	_label.text = "%.0f fps\n%.1f ms" % [fps, frame_ms]

	# Overriding a theme colour dirties the font and forces a reshape, so only
	# do it when the band actually changes.
	var colour: Color = _colour_for(fps)
	if colour != _colour:
		_colour = colour
		_label.add_theme_color_override(&"font_color", colour)

	_accum_s = 0.0
	_frames = 0


func _colour_for(fps: float) -> Color:
	if fps >= WARN_FPS:
		return Color.WHITE
	if fps >= BAD_FPS:
		return Color.YELLOW
	return Color.RED
