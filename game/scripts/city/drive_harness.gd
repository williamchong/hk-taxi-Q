## Puts the car on the start line and keeps it on the map (`P0-5`, `P2-3`).
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
##
## `P2-3` gave it a second job: **resolving where the drive starts**, which used
## to be twelve floats on the Taxi node in `city_drive.tscn`. `RoadSpawn` does
## the work and this applies it, before reading the pose back for the fall floor.
## The order matters and is why the resolution lives here rather than in a node
## of its own — this script is on the scene root, so its `_ready` runs *after*
## every child's, and there is no arrangement of siblings that can beat it to the
## car.
extends Node3D

const GeneratedFares = preload("res://scripts/city/generated_fares.gd")
const GeneratedRoadSurface = preload("res://scripts/city/generated_road_surface.gd")

## How far the resolved start line may sit from the Taxi's authored transform
## before it is worth saying so, in metres.
##
## The authored transform is a fallback now, not the definition, and a fallback
## nobody looks at drifts. Reported rather than corrected: the query is right by
## construction and the literal is only there for a clone with no generated
## assets, so a gap is news about the scene file, not a fault in the spawn.
const AUTHORED_DRIFT_M: float = 1.0

## The car to catch. A NodePath rather than a typed node export because a typed
## one only round-trips through scene files the editor wrote itself, and this
## scene is hand-authored — see `chase_camera.gd`, which hit the same thing.
@export var vehicle_path: NodePath

## How far below its own spawn the car has to get before it counts as gone.
##
## Measured from the spawn rather than stated as a height, so this stays free of
## any particular city (CLAUDE.md hard rule 3). The margin has to clear the
## deepest road below the start line: in Wan Chai that is the Central–Wan Chai
## Bypass Tunnel, bottoming out at −9.08 m against the 6.58 m HKCEC start line,
## so 25 m leaves about **9.3 m** of headroom. ⚠️ That figure moves whenever the
## start line does — and since `P2-3` it is *resolved*, not authored, so it moves
## when the ETL republishes the fare node or the road graph, not only when
## someone edits a scene. Re-check it rather than trusting this line. It also sets how long you spend watching nothing: at this
## profile's 1.6 gravity scale, 25 m is 1.8 seconds.
@export var fall_margin_m: float = 25.0

## Fare node the drive starts at. See `RoadSpawn.DEFAULT_FARE_ID`.
@export var spawn_fare_id: String = RoadSpawn.DEFAULT_FARE_ID

var _vehicle: VehicleController
var _spawn: Transform3D
var _floor_m: float = 0.0
var _falls: int = 0
var _checked_for_road: bool = false


func _ready() -> void:
	_vehicle = get_node_or_null(vehicle_path) as VehicleController
	if _vehicle == null:
		push_warning(
			(
				"Drive harness found no VehicleController at '%s'; nothing will be caught."
				% vehicle_path
			)
		)
		set_physics_process(false)
		return

	_spawn = _place_on_start_line()
	_floor_m = _spawn.origin.y - fall_margin_m


## Move the car onto the resolved start line, and report where that turned out
## to be.
##
## Where it does not resolve the car is left on its authored transform, which is
## returned instead. Falling back rather than refusing, because
## `assets/generated/` is gitignored and a fresh clone has neither graph nor fare
## nodes. There is nothing to drive on either — `_warn_if_there_is_no_road`
## catches that a tick later — so the fallback is about leaving the camera
## somewhere sensible while the real message gets read, not about pretending the
## spawn worked.
func _place_on_start_line() -> Transform3D:
	var authored: Transform3D = _vehicle.global_transform

	# A local: the graph is wanted for this one query and nothing here reads it
	# again. `road_graph_overlay.gd` in this same scene holds its own reference,
	# and `RoadGraph.shared()` is what makes that one parse rather than two.
	var graph: RoadGraph = RoadGraph.shared()
	var pose: RoadSpawn.Pose = RoadSpawn.at_fare_node(
		graph, GeneratedFares.load_fares(), spawn_fare_id, _vehicle.profile.ray_length_m()
	)
	if not pose.resolved():
		push_warning(
			(
				"Spawn falling back to the Taxi's authored transform: %s. %s"
				% [pose.problem, GeneratedFares.missing_hint()]
			)
		)
		return authored

	# The acceptance criterion, asserted where the car is actually placed rather
	# than only in the verify tool. `is_equal_approx` and not `==`: the basis is
	# built from a normalised direction and comes back through float32 rounding.
	assert(
		(-pose.transform.basis.z).is_equal_approx(pose.forward),
		"Spawn basis does not face the edge it was built from — see RoadSpawn.basis_facing."
	)
	if not pose.agrees_with_published():
		push_warning(
			(
				"Fare node '%s' publishes edge %d but the graph query returned %d; the two documents may be from different runs."
				% [pose.fare_id, pose.published_edge_id, pose.edge_id]
			)
		)

	_vehicle.place_at(pose.transform)
	_report_spawn(pose, authored)
	return pose.transform


func _report_spawn(pose: RoadSpawn.Pose, authored: Transform3D) -> void:
	print(
		(
			"start line: %s on edge %d (%s), facing %.1f° — %s"
			% [
				pose.fare_id,
				pose.edge_id,
				pose.road_name_en,
				rad_to_deg(atan2(pose.forward.x, -pose.forward.z)),
				pose.transform.origin
			]
		)
	)
	var drift: float = authored.origin.distance_to(pose.transform.origin)
	if drift > AUTHORED_DRIFT_M:
		print(
			(
				"  the Taxi's authored transform is %.2f m from it — it is only a fallback, but it has drifted"
				% drift
			)
		)


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
