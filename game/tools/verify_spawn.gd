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
## `Q52` gave it a second: **the car has to fit where it is being set down.** The
## bundle publishes a clear corridor width per station and `RoadSpawn` reports it
## without acting on it, deliberately — so this is the only thing that refuses,
## and a rebuild that moves a wall into the start line fails a check instead of
## reaching a driver. It is proven the same way the first one is, in
## `_check_the_guard_can_fire`, because the shipped city cannot prove it: the
## start line stands in 9.00 m of a 3.20 m lane and no fare node lands on any
## blocked edge.
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

## `city.json`'s "no cross-section was judged here", spelled short enough to fit
## the case table in `_check_the_guard_can_fire`.
const UNJUDGED: float = CityManifest.NOT_MEASURED


## One built start line, and the answers the guard must give about it.
##
## A class rather than a bag of string keys, because every field here is read in
## a comparison: through a `Dictionary` each one arrives as a `Variant` and needs
## a cast at the point of use. It also owns the two document shapes it becomes,
## so the edge, the fare node and the expectations cannot fall out of step —
## across three parallel arrays nothing but the loop bound was holding them
## together. `verify_beam_budget.gd`'s `StubRig` is the same idea.
class Case:
	extends RefCounted

	## Which failure this case is here to catch, for the message.
	var why: String
	## Clear width per station, as `city.json` would publish it.
	var clear: PackedFloat32Array
	## What the query must read at the start line.
	var here: float
	## Whether the guard must fire, and whether the whole edge is passable.
	var blocked: bool
	var passable: bool
	## Where this case landed in the built city; `place` fills them.
	var edge_id: int = -1
	var z_m: float = 0.0

	func _init(
		case_why: String,
		case_clear: PackedFloat32Array,
		case_here: float,
		case_blocked: bool,
		case_passable: bool
	) -> void:
		why = case_why
		clear = case_clear
		here = case_here
		blocked = case_blocked
		passable = case_passable

	## Give this case a street of its own. Callers space `z` beyond
	## `nearest_edge`'s 60 m radius, so no query can be answered by another
	## case's geometry and no case can pass on it.
	func place(id: int, z: float) -> void:
		edge_id = id
		z_m = z

	func fare_id() -> String:
		return "f_case_%d" % edge_id

	func label() -> String:
		return "%s (%s)" % [fare_id(), why]

	## The edge, as `roadgraph.json` would publish it — stations along +X.
	func edge(spacing_m: float, lane_m: float) -> Dictionary:
		var polyline: Array[Array] = []
		for station: int in clear.size():
			polyline.append([float(station) * spacing_m, 0.0, z_m])
		return {
			"id": edge_id,
			"polyline": polyline,
			"direction": "both",
			"elevation_level": 0,
			"width_m": lane_m * 2.0,
			"lanes": 2,
			"road_name": {"en": "CASE %d" % edge_id},
		}

	## The fare node, as `fares.json` would publish it. Half a station along, so
	## every start line lands on its edge's **first** segment — which is what
	## makes a wall at a later station a test of the segment rule.
	func fare_node(spacing_m: float) -> Dictionary:
		return {"id": fare_id(), "pos": [spacing_m * 0.5, 0.0, z_m], "nearest_edge": edge_id}

	## Drawn half-widths, one per station. Flat: the lane centre is not what this
	## is proving, and it is asserted against the shipped city elsewhere.
	func halves(lane_m: float) -> PackedFloat32Array:
		var half: PackedFloat32Array = PackedFloat32Array()
		half.resize(clear.size())
		half.fill(lane_m)
		return half


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

	# The lane centre this tool measures against is derived from the published
	# carriageway widths, and `RoadGraph` degrades to the authored street width
	# rather than failing when they are absent. That is a wrong answer shaped
	# like a right one: the spawn reads 1.60 m off the centreline instead of
	# 2.56 m and every assertion below still passes. `verify_road_graph.gd`
	# refuses on the same property for the same reason.
	if not graph.has_carriageway_widths():
		printerr(
			(
				"  FAIL  city.json published no carriageway widths — the lane centre "
				+ "would fall back to the authored street width"
			)
		)
		quit(1)
		return

	# The same argument one gate down, for the other table. An edge with no
	# clearance measurement reads as unknown and unknown reads as clear, so
	# without this the blocked-spawn check below would pass on a bundle that
	# never measured the start line at all — reporting nothing, in the shape of
	# a pass.
	if not graph.has_clearances():
		printerr(
			(
				"  FAIL  city.json published no carriageway clearances — a spawn in a "
				+ "wall would read as clear"
			)
		)
		quit(1)
		return

	var profile: HandlingProfile = load(HANDLING_PATH) as HandlingProfile
	if profile == null:
		printerr("  FAIL  no HandlingProfile at %s" % HANDLING_PATH)
		quit(1)
		return

	# Two lists, run separately on purpose. `_check` grades the **shipped**
	# start line and gives up as soon as it fails to resolve; the guard proof
	# grades the **guard**, on a city built for it, and has to run either way —
	# folded into `_check` it would be skipped by exactly the broken bundle that
	# most needs to know its checks still work.
	var problems: PackedStringArray = _check(graph, fares, profile)
	problems.append_array(_check_the_guard_can_fire(profile.ray_length_m()))
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

	# --- the car fits where it is being set down (Q52) ---------------------
	#
	# What refuses. `RoadSpawn` reports and places anyway on purpose, so this is
	# the only thing standing between a rebuild that moves a wall into the start
	# line and a driver finding it with the bumper.
	if pose.blocked():
		(
			problems
			. append(
				(
					"the spawn stands where %.2f m is clear of the %.2f m lane a car needs (edge %d, %s)"
					% [pose.clear_width_m, pose.lane_width_m, pose.edge_id, pose.road_name_en]
				)
			)
		)
	elif not pose.edge_passable:
		# Not a failure. The car fits where it stands, and `Q51` records 21 edges
		# that are blocked somewhere along them — starting on one is legal and
		# worth knowing.
		print("  note:  edge %d is blocked somewhere along it, though not here" % pose.edge_id)

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


## The guard is proven on a city built to fire it, because the shipped one cannot.
##
## ⚠️ **Every assertion above passes whether the guard works or not.** The start
## line stands in 9.00 m of clear road against a 3.20 m lane, and no fare node in
## the bundle lands on any of the edges `Q51` records as blocked — so a
## `blocked()` hard-wired to `false` would leave this tool green. That is the trap
## `_check_facing` avoids by building the transposed basis and requiring it to be
## rejected, and it is avoided the same way here: five start lines whose answers
## are known, each one required.
##
## Deliberately **not** proven by querying the bundle's own worst edge. A build
## that finally clears all 21 has to pass, which is why
## `verify_road_graph._check_clearance` refuses to depend on the blocked set being
## non-empty either.
##
## The five cases are the whole of the decision, one per way it can go wrong:
##
## 1. **Starved end to end** — it fires.
## 2. **Clear end to end** — it does not, so it is not simply always on.
## 3. **Clear here, walled at the next segment** — it does *not* fire, and
##    `edge_passable` carries that instead. This is why the bar is where the car
##    stands rather than `is_passable`, and it is the case that fails if the two
##    are ever folded together.
## 4. **A junction cap at one end of a walled segment** — it fires. `-1.0` sorts
##    below every real clearance, so taking `minf` across the two stations would
##    read "nothing was judged here" and hide the wall. ⚠️ Not a hypothetical:
##    **562 of Wan Chai's 2959 level-0 segments** have exactly one unmeasured end.
## 5. **Unmeasured at both ends** — it does not fire, and `edge_passable` reads
##    *true*. A station nobody judged is not a wall (45 segments), and what stops
##    a whole bundle of them passing quietly is the `has_clearances()` gate in
##    `_init`, not this.
##
## All five must still **resolve**. Reporting rather than refusing is `Q51`'s
## decision, and a guard that started returning an unresolved pose would put the
## harness back on the authored literal `P2-3` demoted.
##
## Called from `_init` rather than from `_check`, and separately from it: this
## grades the **guard**, where `_check` grades the **shipped** start line and
## gives up the moment that fails to resolve. Folded in, the proof would be
## skipped by exactly the broken bundle that most needs its checks working.
func _check_the_guard_can_fire(ride: float) -> PackedStringArray:
	var problems: PackedStringArray = []

	# Both sides of this city are made up, so the numbers only have to be
	# self-consistent: one lane of 3.20 m over a 6.40 m carriageway, stations
	# 40 m apart, and the start line half a station in — which puts case 3's
	# wall, at the third station, on the far end of the *next* segment.
	var lane_m: float = 3.20
	var spacing_m: float = 40.0
	var cases: Array[Case] = [
		Case.new("starved end to end", PackedFloat32Array([0.5, 0.5]), 0.5, true, false),
		Case.new("clear end to end", PackedFloat32Array([9.0, 9.0]), 9.0, false, true),
		Case.new(
			"clear here, walled further along",
			PackedFloat32Array([9.0, 9.0, 0.5]),
			9.0,
			false,
			false
		),
		Case.new(
			"walled, with a junction cap at one end",
			PackedFloat32Array([UNJUDGED, 0.5]),
			0.5,
			true,
			false
		),
		Case.new(
			"unmeasured at both ends",
			PackedFloat32Array([UNJUDGED, UNJUDGED]),
			UNJUDGED,
			false,
			true
		),
	]

	var edges: Array[Dictionary] = []
	var fare_nodes: Array[Dictionary] = []
	var halves: Dictionary[int, PackedFloat32Array] = {}
	var clears: Dictionary[int, PackedFloat32Array] = {}
	for index: int in cases.size():
		var built: Case = cases[index]
		built.place(index + 1, float(index) * 100.0)
		edges.append(built.edge(spacing_m, lane_m))
		fare_nodes.append(built.fare_node(spacing_m))
		halves[built.edge_id] = built.halves(lane_m)
		clears[built.edge_id] = built.clear

	var manifest := CityManifest.new()
	manifest.lane_width_m = lane_m
	manifest.carriageway_half_width_m = halves
	manifest.carriageway_clear_width_m = clears
	# `nodes` here is the graph's junctions, which this city has none of and
	# nothing under test reads — not `fare_nodes` above.
	var graph: RoadGraph = RoadGraph.from_document(
		{"edges": edges, "nodes": [], "turn_restrictions": []}, manifest
	)
	var fares: Dictionary = {"nodes": fare_nodes}

	for built: Case in cases:
		var pose: RoadSpawn.Pose = RoadSpawn.at_fare_node(graph, fares, built.fare_id(), ride)
		if not pose.resolved():
			problems.append(
				"the guard refused %s instead of reporting it: %s" % [built.label(), pose.problem]
			)
			continue
		if absf(pose.clear_width_m - built.here) > 0.001:
			problems.append(
				(
					"%s reads %.2f m clear where the station published %.2f m"
					% [built.label(), pose.clear_width_m, built.here]
				)
			)
		if pose.blocked() != built.blocked:
			problems.append(
				(
					"%s reads blocked=%s against %.2f m of a %.2f m lane"
					% [built.label(), pose.blocked(), pose.clear_width_m, pose.lane_width_m]
				)
			)
		if pose.edge_passable != built.passable:
			problems.append("%s reads edge_passable=%s" % [built.label(), pose.edge_passable])

	if problems.is_empty():
		print("  guard: all %d built start lines answered as published" % cases.size())
	return problems
