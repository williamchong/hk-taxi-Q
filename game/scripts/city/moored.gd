## Rocks a moored hull at its berth (`P3-102`, `Q254`).
##
## `landmarks.gd` stands one of these at an `afloat` landmark's placement and
## hangs the model under it, so the placement stays the hull at rest and only
## the child moves. The model's origin is its waterline centre, so it heaves,
## rolls about its long axis (local z) and pitches about its beam there.
##
## Visual only: no physics. The model's collider is lifted out of the hull
## onto this node, so it stays at rest — a static body moved every frame is a
## teleport Jolt pays for, and a few centimetres of pose would carry no car.
##
## Runs through a pause, as `water.gdshader`'s `TIME` does, so the boat and
## the water behind a pause menu do not part company.
extends Node3D

const PROFILE: MooredProfile = preload("res://tuning/moored.tres")

var _hull: Node3D


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_hull = get_child(0) as Node3D
	if _hull == null:
		set_process(false)
		return
	for body: Node in _hull.find_children("*", "StaticBody3D", true, false):
		body.reparent(self)


func _process(_delta: float) -> void:
	_hull.transform = pose(PROFILE, Time.get_ticks_msec() / 1000.0)


## The hull's offset from rest at `seconds`: three sines, one per motion, at
## periods that share no small multiple, so the sum never visibly repeats.
static func pose(profile: MooredProfile, seconds: float) -> Transform3D:
	var heave: float = profile.heave_m * sin(TAU * seconds / profile.heave_period_s)
	var roll: float = deg_to_rad(profile.roll_deg) * sin(TAU * seconds / profile.roll_period_s)
	var pitch: float = deg_to_rad(profile.pitch_deg) * sin(TAU * seconds / profile.pitch_period_s)
	return Transform3D(Basis.from_euler(Vector3(pitch, 0.0, roll)), Vector3(0.0, heave, 0.0))
