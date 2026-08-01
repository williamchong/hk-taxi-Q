class_name RoadSpawn
extends RefCounted
## Where a car starts on the real city, resolved from published data (`P2-3`).
##
## One definition, used twice: `drive_harness.gd` places the car with it and
## `tools/verify_spawn.gd` asserts the result headless. That is the whole reason
## it is a static resolver rather than logic inside the harness — a check that
## reimplemented the placement would be checking itself.
##
## ⚠️ **This exists to stop trusting a hand-written `Transform3D` literal, and
## that demotion is the feature.** `city_drive.tscn` still carries one, now only
## as a fallback for a clone with no generated assets. It came with a warning in
## `docs/ARCHITECTURE.md` about how to not transpose it: `Transform3D`'s 12-float
## constructor fills `Basis` *rows*, while "forward" is `-basis.z`, which is a
## *column*. Writing the literal as columns transposes the basis, and a transpose
## is not a 180° flip — it mirrors the heading about world −Z, which is 172°
## wrong on Expo Drive, 180° on a due east-west street and **0°, a silent no-op,
## on a north-south one**. So the error is invisible on exactly the streets an
## eyeball check would trust. `basis_facing` takes a direction, so there is
## nothing left to transpose. This docstring is the home of that argument;
## `verify_spawn.gd` and `city_drive.tscn` point here rather than restating it.
##
## Nothing here knows anything about Hong Kong. The fare node id is an argument,
## the geometry comes from `RoadGraph`, and the height comes from the vehicle's
## own profile (CLAUDE.md hard rule 3).

const GeneratedFares = preload("res://scripts/city/generated_fares.gd")

## The fare node the slice starts at, unless a scene says otherwise.
##
## `f_004` is "Expo Drive eastbound underneath HKCEC Phase II" — a real taxi
## stand in the Transport Department's data, so the car begins where a Hong Kong
## taxi would actually be waiting. A published fact rather than taste, which is
## why the spawn is derived at all.
const DEFAULT_FARE_ID: String = "f_004"

## Air under the tyres at the moment of placement.
##
## The car is dropped, not set down: it starts this far clear of the road and
## settles onto its suspension over the next few ticks. Added to the vehicle's
## own wheel-ray length rather than baked into a single number, so a change to
## `wheel_radius_m` or `suspension_rest_length_m` moves the spawn with it instead
## of burying the car or hanging it in the air.
const DROP_CLEARANCE_M: float = 0.30


## A resolved start line, or an unresolved one carrying why.
class Pose:
	extends RefCounted

	## Where the car goes. Identity unless the query resolved.
	var transform: Transform3D = Transform3D.IDENTITY
	## Edge the query landed on, or -1 for a miss.
	var edge_id: int = -1
	## Closest point on that edge's centreline, at road height. Carried so a
	## consumer measuring the lane offset does not have to re-query for it, and
	## so it is guaranteed to belong to `edge_id` when it does.
	var point: Vector3 = Vector3.ZERO
	## The edge id the fare node itself published, for cross-checking. `fares.py`
	## already did this projection; disagreeing with it means one of the two
	## documents is stale.
	var published_edge_id: int = -1
	## Unit travel direction the car faces. Plan-flat, so the car starts level.
	var forward: Vector3 = Vector3.FORWARD
	## Centre of the nearside lane, at road height — the transform's origin is
	## this lifted by the drop height.
	var lane_centre: Vector3 = Vector3.ZERO
	var fare_id: String = ""
	## Street the car starts on, for the report. May be empty — 74 of Wan Chai's
	## 797 edges publish no English name.
	var road_name_en: String = ""
	## Empty when resolved; otherwise what stopped it, ready to push.
	var problem: String = ""

	func resolved() -> bool:
		return edge_id >= 0

	## True when the query and the published projection name the same edge.
	##
	## Not an error on its own — a fare node on a junction can legitimately be
	## nearest to either arm — but a caller that finds them disagreeing is
	## looking at two documents built from different runs.
	func agrees_with_published() -> bool:
		return published_edge_id < 0 or published_edge_id == edge_id


## Rotation that faces `forward`, level, with no way to transpose it.
##
## `Basis.looking_at` takes the direction as an argument and puts `-Z` on it,
## which is the definition of forward in Godot. Flattened first because the car
## must start level whatever the road's gradient: `RoadGraph.Hit.forward` is
## already plan-flat, so this only matters for a caller passing something else.
static func basis_facing(forward: Vector3) -> Basis:
	var flat := Vector3(forward.x, 0.0, forward.z)
	if flat.length_squared() <= 0.0:
		return Basis.IDENTITY
	return Basis.looking_at(flat.normalized())


## The start line at a fare node, via `P2-2`'s nearest-edge query.
##
## `ride_height_m` is the vehicle's wheel-ray length — `HandlingProfile.ray_length_m`
## — so the drop height is the car's own geometry plus `DROP_CLEARANCE_M` rather
## than a number that has to be re-derived whenever the taxi changes.
##
## The clearance is not a parameter. It is a property of dropping a car onto a
## road rather than of any particular car or start line, and a caller that could
## vary it would put `verify_spawn.gd`'s drop-height check out of step with the
## spawn it is checking.
##
## **The heading is deliberately not supplied.** A zero heading makes
## `nearest_edge` take the edge's own vertex order, and `P1-3` reversed the
## polyline of every backward edge precisely so that order *is* the legal
## direction of travel — the directions `Q12` confirmed against the real street.
## Passing a heading here would let the car's authored rotation decide which way
## a two-way street runs, which is backwards: the street decides.
static func at_fare_node(
	graph: RoadGraph, fares: Dictionary, fare_id: String, ride_height_m: float
) -> Pose:
	var pose := Pose.new()
	pose.fare_id = fare_id

	if graph == null or graph.is_empty():
		pose.problem = "the road graph is empty"
		return pose

	var node: Dictionary = GeneratedFares.node_by_id(fares, fare_id)
	if node.is_empty():
		pose.problem = "no fare node '%s' in %s" % [fare_id, GeneratedFares.PATH]
		return pose
	pose.published_edge_id = int(node.get("nearest_edge", -1))

	var at: Variant = GeneratedFares.position_of(node)
	if at == null:
		pose.problem = "fare node '%s' publishes no usable position" % fare_id
		return pose

	var hit: RoadGraph.Hit = graph.nearest_edge(at)
	if not hit.hit():
		pose.problem = "fare node '%s' resolved to no drivable edge" % fare_id
		return pose

	pose.edge_id = hit.edge_id
	pose.point = hit.point
	pose.forward = hit.forward
	pose.lane_centre = hit.lane_centre
	pose.road_name_en = hit.road_name_en
	pose.transform = Transform3D(
		basis_facing(hit.forward),
		hit.lane_centre + Vector3.UP * (maxf(ride_height_m, 0.0) + DROP_CLEARANCE_M)
	)
	return pose
