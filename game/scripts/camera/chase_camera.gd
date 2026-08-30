class_name ChaseCamera
extends SpringArm3D
## Third-person follow camera.
##
## ⚠️ **This IS the `P2-5` deliverable, and said otherwise until `Q98`.** The
## scope note here read "it is NOT the P2-5 deliverable, which owns look-back
## polish, collision tuning and touch gestures" — written at `P0-5b`, before
## `P2-5` ran. But `P2-5`'s deliverable is *"speed-based FOV and look-back, on
## real geometry"*, and `git show 3aca85a` has both already in this file, so the
## task closed review-passed against code it never modified and the note was
## never revisited. What `P2-5` does still leave open is a touch home for the
## look-back, which `Q97` records as never having been placed on a thumb.
##
## Tuning is `ChaseProfile`, in game/tuning/camera.tres. It lived on @export
## defaults here until `Q98`; chase_profile.gd says why that was hard rule 4 in
## name only.

## NodePaths rather than typed node exports: a typed node export only round-trips
## through scene files the editor wrote itself, so a hand-authored .tscn leaves
## it silently null and the camera never moves.
@export var target_path: NodePath
@export var camera_path: NodePath

@export var profile: ChaseProfile

var target: Node3D

var _camera: Camera3D
var _yaw: float = 0.0
## Speed at which the FOV boost is fully applied. Read from the vehicle's own
## profile so retuning top speed cannot silently desync the FOV ramp.
var _fov_full_kph: float = 140.0


func _ready() -> void:
	target = get_node_or_null(target_path) as Node3D
	_camera = get_node_or_null(camera_path) as Camera3D
	if target == null or _camera == null or profile == null:
		push_error("ChaseCamera needs target_path, camera_path and profile to resolve.")
		set_physics_process(false)
		return

	# The spring arm is what stops the camera passing through buildings.
	spring_length = profile.distance
	top_level = true
	if target is VehicleController:
		_fov_full_kph = (target as VehicleController).profile.max_speed_kph
	_yaw = target.global_rotation.y
	global_position = target.global_position


func _physics_process(delta: float) -> void:
	# Look-back is a yaw flip rather than a second camera: it keeps the spring
	# arm's collision behaviour and costs nothing to hold.
	var desired_yaw: float = target.global_rotation.y + (PI if InputRouter.look_back else 0.0)
	# Exponential rather than constant-rate, which is the whole of `Q98`: the
	# rate is proportional to the error, so a small steering correction barely
	# moves the rig while the look-back flip — a whole PI — still closes
	# promptly. `rotate_toward` gave both the same 401°/s and could express
	# neither. See chase_profile.gd for the arithmetic.
	var yaw_error: float = angle_difference(_yaw, desired_yaw)
	_yaw = wrapf(_yaw + yaw_error * (1.0 - exp(-profile.yaw_response * delta)), -PI, PI)

	var anchor: Vector3 = target.global_position + Vector3.UP * profile.height
	global_position = global_position.lerp(anchor, minf(profile.follow_lag * delta, 1.0))
	global_rotation = Vector3(deg_to_rad(profile.pitch_deg), _yaw, 0.0)

	var kph: float = 0.0
	if target is VehicleController:
		kph = absf((target as VehicleController).forward_speed_kph())
	var fov: float = profile.fov_base + profile.fov_boost * clampf(kph / _fov_full_kph, 0.0, 1.0)
	if not is_equal_approx(fov, _camera.fov):
		_camera.fov = fov
