class_name MenuOrbit
extends Node
## The start menu's hero shot (`P6-1`): the chase rig round the taxi where it
## stands in the showroom, placed by the page the menu shows — circling it on
## HOME, at its tail on OPTIONS, at its kerbside front three-quarter on PLAY
## with the passenger door swung open — and easing from one shot to the next
## as the player moves between pages.
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

var _shot: MenuShot = null
## The car's passenger door, found under `target` by type as `TaxiHire` finds
## it; null on a car without one, which then just keeps its door shut.
var _door: TaxiDoor = null
## Seconds since `_shot` was framed, for its sway.
var _held_s: float = 0.0
## The rig as last placed, each easing toward `_shot`. The yaw is from the
## car's heading, so the shot stays put if the car settles round under it.
var _yaw: float = 0.0
var _distance_m: float = 0.0
var _height_m: float = 0.0
var _pitch_deg: float = 0.0
var _fov_deg: float = 0.0


func _ready() -> void:
	set_process(false)


## Take the rig on HOME's shot. Placed at once so the first frame the menu
## draws over is the orbit's, not a chase frame the rig had not yet left.
func begin() -> void:
	if rig == null or target == null or profile == null or profile.shot_home == null:
		push_warning(
			"MenuOrbit needs rig, target and profile assigned; the menu keeps the chase view."
		)
		return
	_door = null
	for node: Node in target.find_children("*", "", true, false):
		if node is TaxiDoor:
			_door = node as TaxiDoor
			break
	frame(profile.shot_home, true)
	set_process(true)


## Hand the rig back, the door swinging shut as the car pulls away.
func end() -> void:
	set_process(false)
	if _door != null:
		_door.close()


## Move to `shot`, easing there unless `snap`. A turning shot picks up from
## wherever the camera already is, so coming back to HOME never swings back to
## the circle's start.
func frame(shot: MenuShot, snap: bool = false) -> void:
	if shot == null or rig == null or target == null:
		return
	_shot = shot
	_held_s = 0.0
	# Unconditional: `TaxiDoor.is_open` is where the leaf IS, so a page left
	# and re-entered mid-swing would read as already there. Both are idempotent.
	if _door != null:
		if shot.door_open:
			_door.open()
		else:
			_door.close()
	if snap:
		_yaw = wrapf(deg_to_rad(shot.yaw_deg), -PI, PI)
		_distance_m = shot.distance_m
		_height_m = shot.height_m
		_pitch_deg = shot.pitch_deg
		_fov_deg = shot.fov_deg
		_place()


func _process(delta: float) -> void:
	_held_s += delta
	# The chase rig's filter: a first-order ease, so a page changed mid-swing
	# just bends toward the new shot.
	var k: float = ChaseCamera._closed(profile.shot_response, delta)
	if _shot.turn_period_s > 0.0:
		# A turn carries on from wherever the camera stands, unfiltered — a
		# filter chasing a ramp would trail it for good.
		_yaw = wrapf(_yaw + TAU * delta / _shot.turn_period_s, -PI, PI)
	else:
		_yaw = wrapf(_yaw + angle_difference(_yaw, _swayed_yaw()) * k, -PI, PI)
	_distance_m = lerpf(_distance_m, _shot.distance_m, k)
	_height_m = lerpf(_height_m, _shot.height_m, k)
	_pitch_deg = lerpf(_pitch_deg, _shot.pitch_deg, k)
	_fov_deg = lerpf(_fov_deg, _shot.fov_deg, k)
	_place()


func _swayed_yaw() -> float:
	var sway: float = 0.0
	if _shot.sway_period_s > 0.0:
		sway = _shot.sway_deg * sin(TAU * _held_s / _shot.sway_period_s)
	return wrapf(deg_to_rad(_shot.yaw_deg + sway), -PI, PI)


## The rig is `top_level`, so these are world values; the camera hangs off it
## at `spring_length`, colliding as it does under the chase.
func _place() -> void:
	rig.spring_length = _distance_m
	rig.global_position = target.global_position + Vector3.UP * _height_m
	rig.global_rotation = Vector3(deg_to_rad(_pitch_deg), target.global_rotation.y + _yaw, 0.0)
	if rig.camera != null and not is_equal_approx(rig.camera.fov, _fov_deg):
		rig.camera.fov = _fov_deg
