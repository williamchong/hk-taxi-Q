extends Node3D
## ⚠️ SPIKE — the start line and fall-catcher for `city_drive_builtin.tscn`.
##
## A near-copy of `drive_harness.gd`, and deliberately a copy rather than a
## refactor of it. That harness types its car as `VehicleController`, and the
## spike's car is a `VehicleBody3D`; GDScript has no interface to share between
## them, so making one harness serve both means either loosening a shipped type
## annotation or inventing a base class. Neither is worth doing for a spike that
## `P0-5a` has already rejected once — if the built-in vehicle ever won, the two
## harnesses would merge as part of that change, not before it.
##
## What it drops relative to the real one: the authored-transform drift report,
## the published-edge cross-check and the spawn-basis assert. All three are news
## about the scene file, the ETL and `RoadSpawn` rather than about handling, and
## `city_drive.tscn` still makes them all.
##
## See docs/DECISIONS.md `P0-5a`.

## Preloaded rather than referenced by name, exactly as `drive_harness.gd` does:
## neither script carries a `class_name`, so there is no global to reach them by.
const GeneratedFares = preload("res://scripts/city/generated_fares.gd")
const GeneratedRoadSurface = preload("res://scripts/city/generated_road_surface.gd")

@export var vehicle_path: NodePath

## How far below its own spawn the car has to get before it counts as gone.
## Same 25 m as `drive_harness.gd`, for the same reason — see that file.
@export var fall_margin_m: float = 25.0

@export var spawn_fare_id: String = RoadSpawn.DEFAULT_FARE_ID

var _vehicle: BuiltinVehicleController
var _spawn: Transform3D
var _floor_m: float = 0.0
var _falls: int = 0
var _checked_for_road: bool = false


func _ready() -> void:
	_vehicle = get_node_or_null(vehicle_path) as BuiltinVehicleController
	if _vehicle == null:
		push_warning(
			(
				"Builtin drive harness found no BuiltinVehicleController at '%s'; nothing will be caught."
				% vehicle_path
			)
		)
		set_physics_process(false)
		return

	_spawn = _place_on_start_line()
	_floor_m = _spawn.origin.y - fall_margin_m


func _place_on_start_line() -> Transform3D:
	var authored: Transform3D = _vehicle.global_transform
	var graph: RoadGraph = RoadGraph.shared()
	var pose: RoadSpawn.Pose = RoadSpawn.at_fare_node(
		graph, GeneratedFares.load_fares(), spawn_fare_id, _vehicle.profile.ray_length_m()
	)
	if not pose.resolved():
		push_warning(
			(
				"Spawn falling back to the authored transform: %s. %s"
				% [pose.problem, GeneratedFares.missing_hint()]
			)
		)
		return authored

	_vehicle.place_at(pose.transform)
	print(
		(
			"start line: builtin taxi on edge %d (%s), facing %.1f°"
			% [pose.edge_id, pose.road_name_en, CityManifest.bearing_deg(pose.forward)]
		)
	)
	return pose.transform


func _physics_process(_delta: float) -> void:
	if not _checked_for_road:
		_checked_for_road = true
		_warn_if_there_is_no_road()
	if _vehicle.global_position.y > _floor_m:
		return

	_falls += 1
	print("fell out of the world (%d); back to the start line" % _falls)
	_vehicle.place_at(_spawn)


func _warn_if_there_is_no_road() -> void:
	var query := PhysicsRayQueryParameters3D.new()
	query.from = _spawn.origin
	query.to = _spawn.origin + Vector3.DOWN * fall_margin_m
	query.exclude = [_vehicle.get_rid()]
	if not get_world_3d().direct_space_state.intersect_ray(query).is_empty():
		return

	push_warning("Nothing under the start line. " + GeneratedRoadSurface.missing_hint())
	set_physics_process(false)
