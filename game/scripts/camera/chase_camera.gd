class_name ChaseCamera
extends SpringArm3D
## Minimal follow camera for the P0-5 grey-box test.
##
## SCOPE: this exists because vehicle feel cannot be judged through a fixed
## camera — framing is a large part of what "feels fast" means. It is NOT the
## P2-5 deliverable, which owns look-back polish, collision tuning and touch
## gestures. Kept deliberately small so replacing it is cheap.
##
## Tuning lives on @export vars rather than consts so the numbers can be dialled
## in the inspector without a code edit (CLAUDE.md hard rule 4).

## NodePaths rather than typed node exports: a typed node export only round-trips
## through scene files the editor wrote itself, so a hand-authored .tscn leaves
## it silently null and the camera never moves.
@export var target_path: NodePath
@export var camera_path: NodePath

@export_group("Framing")
@export_range(1.0, 15.0, 0.1, "suffix:m") var distance: float = 6.5
@export_range(0.0, 5.0, 0.1, "suffix:m") var height: float = 2.2
@export_range(-60.0, 0.0, 0.5, "suffix:°") var pitch_deg: float = -10.3
## Fraction of the remaining gap closed per second, not a closing speed.
@export_range(1.0, 40.0, 0.5) var follow_lag: float = 12.0
## Angular rate, in radians per second, at which the rig swings to the car's heading.
@export_range(1.0, 30.0, 0.5) var yaw_lag: float = 7.0

@export_group("Speed feel")
@export_range(40.0, 120.0, 1.0, "suffix:°") var fov_base: float = 70.0
@export_range(0.0, 50.0, 1.0, "suffix:°") var fov_boost: float = 18.0

var target: Node3D

var _camera: Camera3D
var _yaw: float = 0.0
## Speed at which the FOV boost is fully applied. Read from the vehicle's own
## profile so retuning top speed cannot silently desync the FOV ramp.
var _fov_full_kph: float = 140.0


func _ready() -> void:
	target = get_node_or_null(target_path) as Node3D
	_camera = get_node_or_null(camera_path) as Camera3D
	if target == null or _camera == null:
		push_error("ChaseCamera needs both target_path and camera_path to resolve.")
		set_physics_process(false)
		return

	# The spring arm is what stops the camera passing through buildings.
	spring_length = distance
	top_level = true
	if target is VehicleController:
		_fov_full_kph = (target as VehicleController).profile.max_speed_kph
	_yaw = target.global_rotation.y
	global_position = target.global_position


func _physics_process(delta: float) -> void:
	# Look-back is a yaw flip rather than a second camera: it keeps the spring
	# arm's collision behaviour and costs nothing to hold.
	var desired_yaw: float = target.global_rotation.y + (PI if InputRouter.look_back else 0.0)
	_yaw = rotate_toward(_yaw, desired_yaw, yaw_lag * delta)

	var anchor: Vector3 = target.global_position + Vector3.UP * height
	global_position = global_position.lerp(anchor, minf(follow_lag * delta, 1.0))
	global_rotation = Vector3(deg_to_rad(pitch_deg), _yaw, 0.0)

	var kph: float = 0.0
	if target is VehicleController:
		kph = absf((target as VehicleController).forward_speed_kph())
	var fov: float = fov_base + fov_boost * clampf(kph / _fov_full_kph, 0.0, 1.0)
	if not is_equal_approx(fov, _camera.fov):
		_camera.fov = fov
