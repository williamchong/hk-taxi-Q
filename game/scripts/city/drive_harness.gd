class_name DriveHarness
## Puts the car on the start line and keeps it on the map (`P0-5`, `P2-3`).
##
## The kerbs are 0.15 m and mountable by design, so leaving the road is easy.
## Until `P3-10` that meant falling out of the world, because everything that was
## not carriageway was void — the terrain was measured at 267 MB of texture
## against a 128 MB budget and left out (`P1-2`). The ground ships now, untextured
## and solid, so mounting a kerb lands on the pavement instead.
##
## This still earns its place: the region has edges, the elevated network is
## closed (`Q13`), and level -1 runs under the terrain (`Q21`). Without it,
## judging the driving means restarting the scene every time you reach one.
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

const GeneratedBasemap = preload("res://scripts/city/generated_basemap.gd")
const GeneratedFares = preload("res://scripts/city/generated_fares.gd")
const GeneratedRegions = preload("res://scripts/city/generated_regions.gd")

## How far the resolved start line may sit from the Taxi's authored transform
## before it is worth saying so, in metres.
##
## The authored transform is a fallback now, not the definition, and a fallback
## nobody looks at drifts. Reported rather than corrected: the query is right by
## construction and the literal is only there for a clone with no generated
## assets, so a gap is news about the scene file, not a fault in the spawn.
const AUTHORED_DRIFT_M: float = 1.0

## The car to catch. Assign in the scene.
## A typed node export since `P5-21`, which measured `Q119`'s null as a missing
## `node_paths=` attribute on the node line, not as the hand-authored scene.
@export var vehicle: VehicleController

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

## How far under the harbour's surface the car's origin has to be before it is
## pulled out (2026-09-25, the user's call: "reset car if fall into water").
##
## The water is a plane with no collider (`region.md`, `Water`): a car that
## leaves the quay lands on the ground the tile stage sank under it, 4 m down,
## and would sit there for ever — the fall margin above never fires, because
## the seabed is 9 m below the start line and the Bypass tunnel 16 m. Judged
## against the plane's own published level (`basemap.json`'s `water_level_m`)
## AND the sea's plan extent, never the level alone: the Cross-Harbour Tunnel
## approach runs 8 m below datum, under sea level and on dry road. One metre is
## the car's roof: the origin is at the hubs, so at 1 m under the surface the
## car is submerged, and a wheel clipping the water's edge at the quay is not.
@export var drown_depth_m: float = 1.0

## Fare node the drive starts at. See `RoadSpawn.DEFAULT_FARE_ID`.
@export var spawn_fare_id: String = RoadSpawn.DEFAULT_FARE_ID

## How far short of that stand the car starts. See `RoadSpawn.DEFAULT_SETBACK_M`.
@export var spawn_setback_m: float = RoadSpawn.DEFAULT_SETBACK_M

## The region `spawn_fare_id` belongs to — `f_001` exists in more than one
## (`P5-9d`). "" is the frame.
@export var spawn_region: String = ""

## The regions asked to hold the road under the start line before the first
## tick (`P5-6`) — every resident region's streamer, since `P5-9c`. Assign in the
## scene; a scene without one — the preview has no harness — simply skips the
## request.
@export var regions: CityRegions

## The fare loop this level runs, for `Main` to hand the HUD beside the car
## (`P3-5a`). Assign in the scene; a level without one has no fare panels.
@export var fares: FareSystem

## The rig that follows the car, snapped wherever this moves it — see
## `ChaseCamera.snap_to_target` for why the rig's own `_ready` cannot cover it.
## Assign in the scene; a scene without one skips the snap.
@export var camera_rig: ChaseCamera

## The rig's slow circle round the parked car for the start menu (`P6-1`).
## Assign in the scene; a scene without one parks the car under the chase view.
@export var attract: MenuOrbit

## Where the car stands for the start menu (`P6-1`): a fare node, resolved
## like the start line, in `spawn_region`. "" parks it on the start line
## itself. The start line is under HKCEC's podium — the menu's orbit there
## looks at a soffit — so the showroom is its own spot and `resume` brings the
## car back to the line the drive begins on.
@export var showroom_fare_id: String = ""

## The world-space fare guide (`fare_guide.gd`), hidden while the menu is up:
## it draws the pending customers' rings and the arrow, which under the menu
## are a game telling you where to go before you have pressed start. Assign
## in the scene; its own next sample shows it again on resume.
@export var guide: Node3D

var _spawn: Transform3D
var _floor_m: float = 0.0
var _falls: int = 0
var _drownings: int = 0
## The harbour's surface, or NAN where no resident region ships a water plane
## — then nothing here can drown.
var _water_level_m: float = NAN
## Every resident region's sea, as plan triangles in the frame — three
## `Vector2` a triangle, moved by the region's offset like the minimap's are.
var _sea: PackedVector2Array = PackedVector2Array()
var _checked_for_road: bool = false


func _ready() -> void:
	if vehicle == null:
		push_warning("Drive harness has no VehicleController assigned; nothing will be caught.")
		set_physics_process(false)
		return

	_spawn = _place_on_start_line()
	_floor_m = _spawn.origin.y - fall_margin_m
	_load_sea()
	_snap_camera()
	_hold_ground()


## Hold the level for the start menu (`P6-1`, `Main`'s call): the pedals read
## nothing, the fare loop holds — the car boots at a stand and would be hailed
## within a second — and the rig circles the car instead of chasing it. The
## physics runs on, so the car settles onto its wheels under the menu, and the
## fall floor and the harbour still catch it.
func park() -> void:
	if vehicle == null:
		return
	vehicle.parked = true
	if guide != null:
		# Hidden AND stopped: its pulse rewrites every pending ring's
		# transform a frame, behind a menu nobody sees it through.
		guide.visible = false
		guide.set_process(false)
	_stand_in_showroom()
	# `is_instance_valid` because the loop frees itself under `--fares=off`
	# (`fare_system.gd`), and only a usable one ever had its tick turned on.
	if is_instance_valid(fares) and fares.usable():
		fares.set_physics_process(false)
	if camera_rig != null:
		camera_rig.set_physics_process(false)
	if attract != null:
		attract.begin()


## Move the car to `showroom_fare_id`, ON the node (no setback: nobody drives
## off from here), with the road held under it first. Where it does not
## resolve the car stays on the start line, and the warning says why — the
## menu still works, over a soffit.
func _stand_in_showroom() -> void:
	if showroom_fare_id.is_empty():
		return
	var pose: RoadSpawn.Pose = RoadSpawn.at_fare_node(
		RoadGraph.shared(),
		GeneratedFares.load_fares(GeneratedFares.path(spawn_region)),
		showroom_fare_id,
		vehicle.profile.ray_length_m(),
		spawn_region,
		0.0
	)
	if not pose.resolved():
		push_warning(
			"Showroom fare node did not resolve; the menu shows the start line: %s" % pose.problem
		)
		return
	if regions != null:
		regions.hold_ground_at(pose.transform.origin)
	vehicle.place_at(pose.transform)
	print("showroom: %s on edge %d (%s)" % [pose.fare_id, pose.edge_id, pose.road_name_en])


## Undo `park`: the drive as it boots without a menu. The rig is snapped, for
## `snap_to_target`'s reason — it has been circling the car, not following it.
func resume() -> void:
	if vehicle == null:
		return
	vehicle.parked = false
	if guide != null:
		guide.set_process(true)
	if attract != null:
		attract.end()
	if not showroom_fare_id.is_empty():
		if regions != null:
			regions.hold_ground_at(_spawn.origin)
		vehicle.place_at(_spawn)
	if camera_rig != null:
		camera_rig.set_physics_process(true)
		camera_rig.snap_to_target()
	if is_instance_valid(fares) and fares.usable():
		fares.set_physics_process(true)


## Before the first `_process`, which is when the streamer first asks where the
## camera is.
func _snap_camera() -> void:
	if camera_rig == null:
		return
	camera_rig.snap_to_target()


## Ask the streamer for the road under the start line before the first physics
## tick (`P5-6`). The road streams by tile now, and a threaded load lands a few
## frames in — frames in which the car would fall through the place the road is
## about to be, `_warn_if_there_is_no_road` would fire on an empty space, and
## every `drive.sh` timeline would shift by however long the disk took, which is
## the determinism `Q27`'s A/B frames rest on. A few small synchronous reads on
## the boot frame keep tick 1 what it was when the road was one mesh.
func _hold_ground() -> void:
	if regions == null:
		return
	regions.hold_ground_at(_spawn.origin)


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
	var authored: Transform3D = vehicle.global_transform

	# A local: the graph is wanted for this one query and nothing here reads it
	# again. `road_graph_overlay.gd` in this same scene holds its own reference,
	# and `RoadGraph.shared()` is what makes that one parse rather than two.
	var graph: RoadGraph = RoadGraph.shared()
	var pose: RoadSpawn.Pose = RoadSpawn.at_fare_node(
		graph,
		GeneratedFares.load_fares(GeneratedFares.path(spawn_region)),
		spawn_fare_id,
		vehicle.profile.ray_length_m(),
		spawn_region,
		spawn_setback_m
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
				% [pose.fare_id, pose.published_edge_id, pose.stand_edge_id]
			)
		)

	vehicle.place_at(pose.transform)
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
				CityManifest.bearing_deg(pose.forward),
				pose.transform.origin
			]
		)
	)
	# Both halves of the clearance answer, in one place: the car is placed either
	# way — `RoadSpawn` says why it does not move it — and this is where a player
	# would otherwise find out by driving into it. After the line above rather
	# than before, so the complaint follows the line that says where. The second
	# branch is not a fault: the car fits where it stands, and an edge a car
	# cannot get down the whole of is news about the drive ahead.
	if pose.blocked():
		push_warning(
			(
				"The start line stands where only %.2f m is clear of the %.2f m lane a car needs (edge %d, %s). Rebuild the region, or start somewhere else with spawn_fare_id."
				% [pose.clear_width_m, pose.lane_width_m, pose.edge_id, pose.road_name_en]
			)
		)
	elif not pose.edge_passable:
		print(
			(
				"  %.2f m clear here, but edge %d is blocked somewhere along it — the way ahead may not be drivable"
				% [pose.clear_width_m, pose.edge_id]
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
	if vehicle.global_position.y <= _floor_m:
		_falls += 1
		print("fell out of the world (%d); back to the start line" % _falls)
		vehicle.place_at(_spawn)
		_snap_camera()
		return
	if _in_the_harbour(vehicle.global_position):
		_drownings += 1
		_pull_out()


## Every resident region's water (`basemap.json`) and the level it is drawn at,
## read once: the plane never moves. A region with no plane contributes no
## triangles, and a bundle with none leaves `_water_level_m` NAN.
func _load_sea() -> void:
	var graph: RoadGraph = RoadGraph.shared()
	for region: String in GeneratedRegions.resident():
		var manifest: CityManifest = CityManifest.load_manifest(region)
		if manifest == null or manifest.water_path.is_empty():
			continue
		var document: Dictionary = GeneratedBasemap.load_basemap(manifest.basemap_path)
		if document.is_empty() or document.get("water_level_m") == null:
			continue
		# One city, one sea: every region publishes the same level, and the first
		# read is the one held.
		if is_nan(_water_level_m):
			_water_level_m = float(document["water_level_m"])
		var offset: Vector3 = graph.region_offset(region)
		for triangle: Variant in document.get("water", []):
			if not triangle is Array or (triangle as Array).size() != 6:
				continue
			var flat: Array = triangle
			for corner: int in 3:
				_sea.append(
					Vector2(
						offset.x + float(flat[corner * 2]), offset.z + float(flat[corner * 2 + 1])
					)
				)


## Under the surface by `drown_depth_m` AND over the sea in plan. The depth
## gate first: it is one compare a tick, and the triangle walk runs only for a
## car that is already below sea level — the tunnel approach, or the harbour.
func _in_the_harbour(at: Vector3) -> bool:
	if is_nan(_water_level_m) or at.y > _water_level_m - drown_depth_m:
		return false
	var plan := Vector2(at.x, at.z)
	for first: int in range(0, _sea.size(), 3):
		if Geometry2D.point_is_inside_triangle(plan, _sea[first], _sea[first + 1], _sea[first + 2]):
			return true
	return false


## Back onto the nearest road, facing the way the car was going, dropped from
## the spawn's own height; the start line where no road is within reach — a
## car 300 m out in the harbour has no nearest street worth the name.
func _pull_out() -> void:
	var graph: RoadGraph = RoadGraph.shared()
	var heading: Vector3 = -vehicle.global_transform.basis.z
	var hit: RoadGraph.Hit = graph.nearest_edge(vehicle.global_position, heading)
	var pose: Transform3D = _spawn
	if hit.edge_id >= 0:
		var lift: float = vehicle.profile.ray_length_m() + RoadSpawn.DROP_CLEARANCE_M
		pose = Transform3D(RoadSpawn.basis_facing(hit.forward), hit.lane_centre + Vector3.UP * lift)
	print(
		(
			"in the harbour (%d); back onto %s"
			% [
				_drownings,
				"the start line" if hit.edge_id < 0 else "edge %d" % hit.edge_id,
			]
		)
	)
	if regions != null:
		regions.hold_ground_at(pose.origin)
	vehicle.place_at(pose)
	_snap_camera()


## Stop before the car falls for ever on a clone where the ETL has not been run.
##
## `assets/generated/` is gitignored, so a fresh checkout has no road chunks and
## therefore no collider at all — the car would drop through the start line,
## respawn, and drop again every two seconds with nothing on screen to explain
## why. Checked once, on the first tick, because the physics space has nothing
## to query during `_ready`.
func _warn_if_there_is_no_road() -> void:
	var query := PhysicsRayQueryParameters3D.new()
	query.from = _spawn.origin
	query.to = _spawn.origin + Vector3.DOWN * fall_margin_m
	query.exclude = [vehicle.get_rid()]
	if not get_world_3d().direct_space_state.intersect_ray(query).is_empty():
		return

	push_warning("Nothing under the start line. " + CityManifest.road_missing_hint())
	set_physics_process(false)
