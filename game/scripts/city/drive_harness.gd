## Keeps the car on the map while the real city is being driven.
##
## The region ships with no ground: the terrain was measured at 267 MB of
## texture against a 128 MB budget and left out (`P1-2`), so everything that is
## not carriageway is void. The kerbs are 0.15 m and mountable by design, which
## means leaving the road is easy and falling out of the world is what happens
## next. Without this, judging the driving means restarting the scene every time
## you clip a corner.
##
## A dev harness, not a game system. `P3-*` owns real respawn rules — where the
## player returns to, what it costs them, and what the fare does meanwhile. This
## only decides *when* to recover; `VehicleController.place_at` does the work,
## because the state that has to be reset belongs to the car.
extends Node3D

const GeneratedRoadSurface = preload("res://scripts/city/generated_road_surface.gd")

## The car to catch. A NodePath rather than a typed node export because a typed
## one only round-trips through scene files the editor wrote itself, and this
## scene is hand-authored — see `chase_camera.gd`, which hit the same thing.
@export var vehicle_path: NodePath

## How far below its own spawn the car has to get before it counts as gone.
##
## Measured from the spawn rather than stated as a height, so this stays free of
## any particular city (CLAUDE.md hard rule 3). The margin has to clear the
## deepest road below the start line: in Wan Chai that is the Cross Harbour
## Tunnel, whose surface bottoms out at −9.1 m against a 4.7 m spawn, so 25 m is
## about eleven metres of headroom. It also sets how long you spend watching
## nothing — at this profile's 1.6 gravity scale, 25 m is 1.8 seconds.
@export var fall_margin_m: float = 25.0

var _vehicle: VehicleController
var _spawn: Transform3D
var _floor_m: float = 0.0
var _falls: int = 0
var _checked_for_road: bool = false


func _ready() -> void:
	_vehicle = get_node_or_null(vehicle_path) as VehicleController
	if _vehicle == null:
		push_warning(
			"Drive harness found no VehicleController at '%s'; nothing will be caught."
			% vehicle_path
		)
		set_physics_process(false)
		return
	# Read from the scene rather than exported separately, so the car's authored
	# transform stays the one definition of where the drive starts.
	_spawn = _vehicle.global_transform
	_floor_m = _spawn.origin.y - fall_margin_m


func _physics_process(_delta: float) -> void:
	if not _checked_for_road:
		_checked_for_road = true
		_warn_if_there_is_no_road()
	if _vehicle.global_position.y > _floor_m:
		return

	_falls += 1
	print("fell out of the world (%d); back to the start line" % _falls)
	_vehicle.place_at(_spawn)


## Stop before the car falls for ever on a clone where the ETL has not been run.
##
## `assets/generated/` is gitignored, so a fresh checkout has no `roads.glb` and
## therefore no collider at all — the car would drop through the start line,
## respawn, and drop again every two seconds with nothing on screen to explain
## why. Checked once, on the first tick, because the physics space has nothing
## to query during `_ready`.
func _warn_if_there_is_no_road() -> void:
	var query := PhysicsRayQueryParameters3D.new()
	query.from = _spawn.origin
	query.to = _spawn.origin + Vector3.DOWN * fall_margin_m
	query.exclude = [_vehicle.get_rid()]
	if not get_world_3d().direct_space_state.intersect_ray(query).is_empty():
		return

	push_warning("Nothing under the start line. " + GeneratedRoadSurface.missing_hint())
	set_physics_process(false)
