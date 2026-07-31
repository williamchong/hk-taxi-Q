## Free-fly camera for inspecting generated geometry.
##
## A dev tool. The game's real camera is `chase_camera.gd` (`P2-5`); this exists
## so ETL output can be flown around before there is a car to sit behind.
##
## Reads raw input rather than going through `InputRouter`, deliberately: the
## router's action set is the *game's* (steer, accelerate, drift) and adding
## fly-camera bindings to it would put dev-only actions in the shipped map.
extends Camera3D

@export var speed_mps: float = 60.0
@export var boost_multiplier: float = 5.0
@export var look_sensitivity: float = 0.003

## Node emitting `built(low, high)` to frame on startup — normally the tile
## preview. Framing what was actually loaded keeps this region-agnostic; a
## hardcoded look-at target would be a Hong Kong fact in the viewer.
@export var frame_target: NodePath

var _yaw: float = 0.0
var _pitch: float = 0.0
var _mouse_captured: bool = false


func _ready() -> void:
	_store_rotation()
	if frame_target.is_empty():
		return
	var source: Node = get_node_or_null(frame_target)
	if source != null and source.has_signal("built"):
		source.built.connect(frame)


## Pull back far enough to see the whole box, looking down at its centre.
func frame(low: Vector3, high: Vector3) -> void:
	var centre: Vector3 = (low + high) * 0.5
	var span: float = maxf(high.x - low.x, high.z - low.z)
	global_position = Vector3(centre.x, high.y + span * 0.35, high.z + span * 0.5)
	look_at(centre, Vector3.UP)
	_store_rotation()


func _store_rotation() -> void:
	# Euler order is YXZ, so yaw-then-pitch with zero roll round-trips exactly.
	_yaw = rotation.y
	_pitch = rotation.x


func _unhandled_input(event: InputEvent) -> void:
	var button := event as InputEventMouseButton
	if button != null and button.pressed and button.button_index == MOUSE_BUTTON_LEFT:
		# Left button only: the wheel is also an InputEventMouseButton, so a
		# bare `pressed` check would capture the cursor on every scroll.
		_set_captured(true)
		return

	var key := event as InputEventKey
	if key != null and key.pressed and key.keycode == KEY_ESCAPE:
		_set_captured(false)
		return

	var motion := event as InputEventMouseMotion
	if motion != null and _mouse_captured:
		_yaw -= motion.relative.x * look_sensitivity
		# Stop just short of vertical: at exactly +/-90 degrees the yaw axis and
		# the view direction align and the camera rolls.
		_pitch = clampf(_pitch - motion.relative.y * look_sensitivity, -1.5, 1.5)
		rotation = Vector3(_pitch, _yaw, 0.0)


func _process(delta: float) -> void:
	# -Z is forward, so W is -Z.
	var move := Vector3(_axis(KEY_D, KEY_A), _axis(KEY_E, KEY_Q), _axis(KEY_S, KEY_W))
	if move == Vector3.ZERO:
		return

	var metres: float = speed_mps * delta
	if Input.is_physical_key_pressed(KEY_SHIFT):
		metres *= boost_multiplier
	# Q/E stay world-vertical so climbing does not depend on where you look.
	translate(Vector3(move.x, 0.0, move.z).normalized() * metres)
	global_position.y += move.y * metres


func _axis(positive: Key, negative: Key) -> float:
	# Physical keycodes, matching how `project.godot` binds the game's own
	# actions. Layout-dependent `is_key_pressed` would turn WASD into ZQSD on an
	# AZERTY keyboard while the car kept its original keys.
	return (
		float(Input.is_physical_key_pressed(positive))
		- float(Input.is_physical_key_pressed(negative))
	)


func _set_captured(captured: bool) -> void:
	_mouse_captured = captured
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if captured else Input.MOUSE_MODE_VISIBLE
