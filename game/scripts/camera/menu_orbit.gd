class_name MenuOrbit
extends Node
## The start menu's hero shot (`P6-1`): the chase rig circling the taxi where
## it stands on the start line, slowly, until the player starts.
##
## Drives the SAME rig the chase uses rather than a second camera. `CityRegions`
## streams by the rig's `Camera3D`, so a second camera made current would leave
## the streamer measuring from a rig parked elsewhere; moving the rig keeps one
## camera, one streamer and the spring arm's own collision under the menu. The
## rig's `_physics_process` is off while this runs — `DriveHarness.park` turns
## it off and `resume` turns it back on and snaps — so the two never write the
## rig on one tick.
##
## Every number is `MenuProfile`'s (hard rule 4).

## The rig to move, and the car to circle. Assign in the scene.
@export var rig: ChaseCamera
@export var target: Node3D
@export var profile: MenuProfile

var _angle: float = 0.0


func _ready() -> void:
	set_process(false)


## Take the rig. Placed at once so the first frame the menu draws over is the
## orbit's, not a chase frame the rig had not yet left.
func begin() -> void:
	if rig == null or target == null or profile == null:
		push_warning(
			"MenuOrbit needs rig, target and profile assigned; the menu keeps the chase view."
		)
		return
	_angle = wrapf(target.global_rotation.y + deg_to_rad(profile.orbit_start_deg), -PI, PI)
	# Once: the chase rewrites its own length every tick on resume.
	rig.spring_length = profile.orbit_distance_m
	set_process(true)
	_place()


func end() -> void:
	set_process(false)


func _process(delta: float) -> void:
	_angle = wrapf(_angle + TAU * delta / profile.orbit_period_s, -PI, PI)
	_place()


## The rig is `top_level`, so these are world values; the camera hangs off it
## at `spring_length`, colliding as it does under the chase.
func _place() -> void:
	rig.global_position = target.global_position + Vector3.UP * profile.orbit_height_m
	rig.global_rotation = Vector3(deg_to_rad(profile.orbit_pitch_deg), _angle, 0.0)
	if rig.camera != null and not is_equal_approx(rig.camera.fov, profile.orbit_fov_deg):
		rig.camera.fov = profile.orbit_fov_deg
