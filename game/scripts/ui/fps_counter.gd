extends CanvasLayer
## Performance overlay: frame rate and average frame time.
##
## Autoloaded, so it survives scene changes. Frame time is averaged from real
## deltas rather than derived from the rounded FPS integer — 60 and 60.9 fps
## both round to "16.7 ms" otherwise, which is exactly the resolution needed to
## spot a hitch.
##
## Debug builds only, unless launched with --fps. Release builds must not pay
## for a per-frame overlay against a <150 draw call budget.

## Thresholds come from the 60fps mobile target in docs/ARCHITECTURE.md.
const WARN_FPS: float = 55.0
const BAD_FPS: float = 45.0
const UPDATE_INTERVAL_S: float = 0.25
const FORCE_ARG: String = "--fps"

var _label: Label
var _accum_s: float = 0.0
var _frames: int = 0
var _colour: Color = Color.WHITE


func _ready() -> void:
	if not OS.is_debug_build() and not OS.get_cmdline_args().has(FORCE_ARG):
		# queue_free() only takes effect at the end of the frame, so stop
		# processing first or _process runs once with a null label.
		set_process(false)
		queue_free()
		return

	layer = 128
	process_mode = Node.PROCESS_MODE_ALWAYS

	_label = Label.new()
	_label.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	_label.offset_left = -160.0
	_label.offset_top = 8.0
	_label.offset_right = -8.0
	_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_label.add_theme_color_override(&"font_color", _colour)
	_label.add_theme_color_override(&"font_outline_color", Color.BLACK)
	_label.add_theme_constant_override(&"outline_size", 4)
	add_child(_label)


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
