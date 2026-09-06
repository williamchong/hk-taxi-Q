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
## Where the look-back button is read from. A `NodePath` to the `InputRouter`
## autoload rather than its global name, for `VehicleController.input_path`'s
## reason (`Q119`); a rig with no router simply never looks back.
@export var input_path: NodePath = ^"/root/InputRouter"

var target: Node3D

var _camera: Camera3D
var _input: Node = null
var _yaw: float = 0.0
## Speed at which the FOV boost is fully applied. Seeded from the profile and
## overridden by a VehicleController target's own HandlingProfile — see
## chase_profile.gd's fov_full_kph for which of those the shipped scenes use.
var _fov_full_kph: float = 0.0


func _ready() -> void:
	target = get_node_or_null(target_path) as Node3D
	_camera = get_node_or_null(camera_path) as Camera3D
	_input = get_node_or_null(input_path)
	if target == null or _camera == null or profile == null:
		push_error("ChaseCamera needs target_path, camera_path and profile to resolve.")
		set_physics_process(false)
		return

	# The profile ships no defaults, so a .tres missing a key reads as zero. These
	# two render perfectly while being wrong — a rig that never yaws, and a spring
	# arm collapsed into the car — which is why they are caught here and not left
	# to be noticed. vehicle_controller.gd guards its own profile the same way.
	assert(profile.distance > 0.0, "ChaseProfile.distance is zero.")
	assert(profile.follow_response > 0.0, "ChaseProfile.follow_response is zero.")
	assert(profile.yaw_response > 0.0, "ChaseProfile.yaw_response is zero.")
	assert(profile.fov_full_kph > 0.0, "ChaseProfile.fov_full_kph is zero.")

	top_level = true
	_fov_full_kph = profile.fov_full_kph
	if target is VehicleController:
		_fov_full_kph = (target as VehicleController).profile.max_speed_kph
	_yaw = target.global_rotation.y
	global_position = target.global_position


func _physics_process(delta: float) -> void:
	# Look-back is a yaw flip rather than a second camera: it keeps the spring
	# arm's collision behaviour and costs nothing to hold.
	var look_back: bool = _input != null and bool(_input.get(&"look_back"))
	var desired_yaw: float = target.global_rotation.y + (PI if look_back else 0.0)
	# Exponential rather than constant-rate, which is the whole of `Q98`: the
	# rate is proportional to the error, so a small steering correction barely
	# moves the rig while the look-back flip — a whole PI — still closes
	# promptly. `rotate_toward` gave both the same 401°/s and could express
	# neither. See chase_profile.gd for the arithmetic.
	# ⚠️ The direction of the look-back swing is set by the sign of the residual
	# yaw lag, because angle_difference returns -PI at exactly PI. Turning one way
	# swings the camera one way, which is what you want — but settled and straight
	# that residual is float noise, so two identical presses can swing opposite
	# ways. Harmless, and not worth a bias term that would lie about the frame.
	var yaw_error: float = angle_difference(_yaw, desired_yaw)
	_yaw = wrapf(_yaw + yaw_error * _closed(profile.yaw_response, delta), -PI, PI)

	# Written every tick rather than at _ready, so a live edit to any dial takes
	# effect on the next frame — vehicle_controller.gd states that house rule.
	spring_length = profile.distance
	var anchor: Vector3 = target.global_position + Vector3.UP * profile.height
	global_position = global_position.lerp(anchor, _closed(profile.follow_response, delta))
	global_rotation = Vector3(deg_to_rad(profile.pitch_deg), _yaw, 0.0)

	var kph: float = 0.0
	if target is VehicleController:
		kph = absf((target as VehicleController).forward_speed_kph())
	var fov: float = profile.fov_base + profile.fov_boost * clampf(kph / _fov_full_kph, 0.0, 1.0)
	if not is_equal_approx(fov, _camera.fov):
		_camera.fov = fov


## Fraction of a remaining gap a first-order filter closes over `delta` at rate
## `per_second`.
##
## ⚠️ **`1 - exp(-k·dt)`, not `k·dt`.** hud.gd argues this at length for the
## acceleration bar: the linear form is only that curve's first-order
## approximation, it needs a clamp to stay under 1, and its effective time
## constant shortens as frames are dropped. Here delta is a fixed 1/60 so nothing
## drifts — but the two smoothers above are the same filter and there is no
## reason for them to be two different ones.
static func _closed(per_second: float, delta: float) -> float:
	return 1.0 - exp(-per_second * delta)
