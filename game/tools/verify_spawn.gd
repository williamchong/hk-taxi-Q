## Checks the resolved start line against the edge it was built from (`P2-3`).
##
##     godot --headless --path game --script res://tools/verify_spawn.gd
##
## The sixth verify tool, and it exists for one acceptance criterion: **spawn
## orientation asserted against its edge vector**. `P2-3` names that criterion
## because the bug it guards against already shipped once — a transposed basis
## survived a full user drive-through and was caught from the driver's seat when
## the harbour turned out to be on the wrong side.
##
## ⚠️ **The orientation check is deliberately proven non-vacuous here, in the
## tool.** A transpose is undetectable on a north-south street — `road_spawn.gd`
## is where that argument lives — so a tool that only asserted the good case
## would pass on such a spawn with the bug present. The transposed basis is
## therefore built and required to *fail*, and the discriminating angle floored.
##
## Exits non-zero if the spawn cannot be resolved or any check fails.
extends SceneTree

const GeneratedFares = preload("res://scripts/city/generated_fares.gd")

## The profile the drive scene runs, for the wheel-ray length the drop height is
## built from. Loaded rather than assumed so a retuned car moves this check with
## it.
const HANDLING_PATH: String = "res://tuning/handling.tres"

## How far apart the good basis and its transpose must be before this street can
## discriminate between them. Below it the check would pass either way and is
## reporting nothing.
const MIN_TRANSPOSE_ANGLE_DEG: float = 10.0

## Agreement required between `-basis.z` and the edge's travel direction. Tighter
## than any error the bug produces and looser than float32 rounding.
const MAX_FACING_ERROR_DEG: float = 0.1

## The car must start off the centreline — that is where opposed carriageway
## ribbons overlap and a suspension ray hunts between two coplanar triangles.
const MIN_LANE_OFFSET_M: float = 0.5


func _init() -> void:
	# `RoadGraph.shared()` rather than the `from_document` preamble the other
	# graph-reading tools use: they need the raw document to iterate edges, and
	# this one only needs the queries. Neither loader is re-explained on failure —
	# both have already pushed the reason and the command that fixes it.
	var graph: RoadGraph = RoadGraph.shared()
	var fares: Dictionary = GeneratedFares.load_fares()
	if graph.is_empty() or fares.is_empty():
		quit(1)
		return

	var profile: HandlingProfile = load(HANDLING_PATH) as HandlingProfile
	if profile == null:
		printerr("  FAIL  no HandlingProfile at %s" % HANDLING_PATH)
		quit(1)
		return

	var problems: PackedStringArray = _check(graph, fares, profile)
	for problem: String in problems:
		printerr("  FAIL  ", problem)
	if problems.is_empty():
		print("  ok    ", GeneratedFares.PATH)
	quit(1 if not problems.is_empty() else 0)


func _check(graph: RoadGraph, fares: Dictionary, profile: HandlingProfile) -> PackedStringArray:
	var problems: PackedStringArray = []

	var ride: float = profile.ray_length_m()
	if ride <= 0.0:
		problems.append("the handling profile gives a wheel-ray length of %.3f m" % ride)
		return problems

	var pose: RoadSpawn.Pose = RoadSpawn.at_fare_node(graph, fares, RoadSpawn.DEFAULT_FARE_ID, ride)
	if not pose.resolved():
		problems.append("the spawn did not resolve: %s" % pose.problem)
		return problems

	# --- the spawn is on a street a car is allowed on (Q13) ----------------
	if not graph.is_drivable(pose.edge_id):
		problems.append(
			(
				"the spawn landed on edge %d, which is at level %d"
				% [pose.edge_id, graph.level_of(pose.edge_id)]
			)
		)
	if not pose.agrees_with_published():
		problems.append(
			(
				"fare node '%s' publishes edge %d but the query returned %d"
				% [pose.fare_id, pose.published_edge_id, pose.edge_id]
			)
		)

	# --- P2-3: the orientation, against the edge vector --------------------
	problems.append_array(_check_facing(pose))

	# --- the car starts in its lane, directly above the target -------------
	var offset: float = RoadGraph.plan_distance(pose.transform.origin, pose.lane_centre)
	if offset > 0.001:
		problems.append("the spawn is %.3f m from its own lane centre in plan" % offset)

	# Against `pose.point`, which the query guarantees belongs to `pose.edge_id`.
	# Re-querying here would be free but wrong: the nearest centreline to the lane
	# centre can be a *neighbouring* edge, and testing that against this edge's
	# travel direction compares two unrelated streets.
	var to_lane: Vector3 = pose.lane_centre - pose.point
	if to_lane.length() > 0.001:
		if to_lane.normalized().dot(RoadGraph.left_of(pose.forward)) < 0.99:
			problems.append("the spawn is not in the nearside lane — Hong Kong drives on the left")

	# --- and clear of every seam, not only its own edge's ------------------
	#
	# Asked from the lane centre with no constraint on which edge answers, which
	# is stricter than measuring against `pose.point`: the hazard is opposed
	# carriageway ribbons overlapping, so a *neighbouring* centreline being too
	# close is exactly the case worth catching.
	var nearest: RoadGraph.Hit = graph.nearest_edge(pose.lane_centre)
	if not nearest.hit():
		problems.append("nothing resolved under the spawn's own lane centre")
	elif nearest.distance < MIN_LANE_OFFSET_M:
		problems.append(
			(
				"the spawn is %.3f m from edge %d's centreline, inside the %.2f m the seam needs"
				% [nearest.distance, nearest.edge_id, MIN_LANE_OFFSET_M]
			)
		)

	# --- the drop height is the car's own geometry -------------------------
	var lift: float = pose.transform.origin.y - pose.lane_centre.y
	if absf(lift - (ride + RoadSpawn.DROP_CLEARANCE_M)) > 0.001:
		problems.append(
			(
				"the spawn is %.3f m above the road, expected %.2f m ray + %.2f m clearance"
				% [lift, ride, RoadSpawn.DROP_CLEARANCE_M]
			)
		)

	if problems.is_empty():
		print(
			(
				"  spawn: %s on edge %d (%s), %.2f m off the centreline, %.2f m of air"
				% [pose.fare_id, pose.edge_id, pose.road_name_en, to_lane.length(), lift]
			)
		)
	return problems


## `-basis.z` is the edge's travel direction, and a transposed basis is not.
##
## Both halves are the check. The first is the criterion; the second is what
## stops the first passing vacuously on a street where the two agree.
func _check_facing(pose: RoadSpawn.Pose) -> PackedStringArray:
	var problems: PackedStringArray = []

	var facing: Vector3 = -pose.transform.basis.z
	var error_deg: float = rad_to_deg(facing.angle_to(pose.forward))
	# The bug, built on purpose. `Transform3D`'s 12-float constructor fills rows
	# while forward is a column, so writing the literal as columns produces
	# exactly this basis — and it has to be rejected.
	var transposed: Vector3 = -pose.transform.basis.transposed().z
	var separation_deg: float = rad_to_deg(transposed.angle_to(pose.forward))

	# Both angles go into whichever message comes out. They are what either
	# failure is triaged with, and reporting them separately would have printed a
	# report-shaped line beside a FAIL, or withheld the facing error from the one
	# message that most needs it.
	if error_deg > MAX_FACING_ERROR_DEG:
		problems.append(
			(
				(
					"the spawn faces %.3f° off edge %d — travel is %s, the car faces %s, and a "
					+ "transposed basis would be %.1f° off"
				)
				% [error_deg, pose.edge_id, pose.forward, facing, separation_deg]
			)
		)
	elif separation_deg < MIN_TRANSPOSE_ANGLE_DEG:
		problems.append(
			(
				(
					"the spawn faces %.4f° off edge %d, but a transposed basis is only %.2f° from "
					+ "the same answer — this check cannot see the bug it exists to catch, so move "
					+ "the spawn off a north-south street or assert it somewhere else"
				)
				% [error_deg, pose.edge_id, separation_deg]
			)
		)
	else:
		print(
			(
				"  facing: %.4f° off the edge vector; a transposed basis would be %.1f° off"
				% [error_deg, separation_deg]
			)
		)
	return problems
