## Checks `RoadGraph`'s queries against the graph they read, headless (`P2-2`).
##
##     godot --headless --path game --script res://tools/verify_road_graph.gd
##
## The fourth verify tool, and the first that asserts *logic* rather than the
## shape of a generated asset. `P2-2`'s acceptance criteria say the queries are
## unit-tested, and this repo has no GDScript test framework — it has three tools
## that assert facts and exit non-zero, run by `tools/check.sh` for their exit
## code. Adding a fourth is a smaller change than adding a dependency, and it
## lands the assertions somewhere CI already runs.
##
## The load-bearing check is `Q13`: `nearest_edge` must never hand a car an
## off-grade edge. Everything else here exists so that a query which quietly
## stopped working could not pass by returning nothing.
##
## Exits non-zero if the graph is missing or any check fails.
extends SceneTree

const GeneratedRoadGraph = preload("res://scripts/city/generated_road_graph.gd")

## Below this and the index is not doing its job — Wan Chai has 737 level-0
## edges today. A floor rather than an equality: the region can grow.
const MIN_DRIVABLE_EDGES: int = 100

## A query this far from any road must miss rather than reach across the region.
const FAR_AWAY: Vector3 = Vector3(-5000.0, 0.0, -5000.0)

## `P2-2`'s last acceptance criterion, as one query's budget in microseconds.
const QUERY_BUDGET_USEC: float = 1000.0

## Plan spacing of the timing lattice, in metres. 10 m over Wan Chai is ~15,000
## probes: enough that a p99 is a property of the code rather than of the sample,
## and fine enough that the lattice lands on roads as well as between them.
const PROBE_SPACING_M: float = 10.0

## Queries run before timing starts, so the first call's lazy allocation is not
## charged to the distribution it would otherwise dominate.
const WARMUP_PROBES: int = 200


func _init() -> void:
	# Neither loader is re-explained here. Both have already pushed the reason
	# and the command that fixes it — and for a stale schema that reason is not
	# the missing-file hint, so repeating one would name the wrong fix half the
	# time. `verify_city.gd` and `verify_tiles.gd` refuse for the same reason.
	var document: Dictionary = GeneratedRoadGraph.load_graph()
	var manifest: CityManifest = CityManifest.load_manifest()
	if document.is_empty() or manifest == null:
		quit(1)
		return

	var graph: RoadGraph = RoadGraph.from_document(document, manifest.carriageway_half_width_m)
	var problems: PackedStringArray = _check(graph, document, manifest.bounds)
	for problem: String in problems:
		printerr("  FAIL  ", problem)
	if problems.is_empty():
		print("  ok    ", GeneratedRoadGraph.PATH)
	quit(1 if not problems.is_empty() else 0)


func _check(graph: RoadGraph, document: Dictionary, bounds: AABB) -> PackedStringArray:
	var problems: PackedStringArray = []
	var edges: Array = document.get("edges", [])

	if graph.edge_count() < 1:
		problems.append("the graph parsed no edges")
		return problems
	if graph.indexed_segment_count() < 1:
		problems.append("no drivable segments were indexed")
		return problems

	# --- the graph keeps every edge, drivable or not -----------------------
	var off_grade: Array[int] = []
	var drivable: Array[int] = []
	for edge: Dictionary in edges:
		var id: int = int(edge.get("id", -1))
		if int(edge.get("elevation_level", 0)) == 0:
			drivable.append(id)
		else:
			off_grade.append(id)
		if graph.polyline_of(id).is_empty() and (edge.get("polyline", []) as Array).size() >= 2:
			problems.append("edge %d is in the document but not in the graph" % id)
	if drivable.size() < MIN_DRIVABLE_EDGES:
		problems.append(
			"%d drivable edges, expected at least %d" % [drivable.size(), MIN_DRIVABLE_EDGES]
		)
	if off_grade.is_empty():
		problems.append(
			(
				"no off-grade edges in the document — the Q13 check below cannot fail, "
				+ "so it would pass vacuously"
			)
		)

	# --- Q13: no query may return an off-grade edge ------------------------
	#
	# Asked where it is most likely to break rather than at random: every vertex
	# of every off-grade edge, which is exactly where a flyover centreline is
	# nearest in plan to the query point. A car under the Canal Road Flyover is
	# this query.
	var off_grade_hits: int = 0
	var probes: int = 0
	for edge: Dictionary in edges:
		if int(edge.get("elevation_level", 0)) == 0:
			continue
		for raw: Array in edge.get("polyline", []):
			probes += 1
			var hit: RoadGraph.Hit = graph.nearest_edge(Vector3(raw[0], raw[1], raw[2]))
			if hit.hit() and not graph.is_drivable(hit.edge_id):
				off_grade_hits += 1
				if off_grade_hits == 1:
					problems.append(
						(
							"nearest_edge returned off-grade edge %d (level %d) under %s"
							% [hit.edge_id, graph.level_of(hit.edge_id), str(raw)]
						)
					)
	if off_grade_hits > 0:
		problems.append(
			"%d of %d off-grade probes resolved to an off-grade edge" % [off_grade_hits, probes]
		)
	if probes == 0:
		problems.append("the Q13 check ran no probes")

	# --- queries resolve where a car actually is ---------------------------
	#
	# Every drivable edge's own midpoint must resolve to that edge. This is the
	# check that fails if the index buckets wrongly: a cell key computed with the
	# wrong stride still returns *an* edge, just not the one underfoot.
	var wrong: int = 0
	var missed: int = 0
	var first: String = ""
	for edge: Dictionary in edges:
		if int(edge.get("elevation_level", 0)) != 0:
			continue
		var points: Array = edge.get("polyline", [])
		if points.size() < 2:
			continue
		var mid: Array = points[floori(points.size() / 2.0)]
		var at := Vector3(mid[0], mid[1], mid[2])
		var hit: RoadGraph.Hit = graph.nearest_edge(at)
		if not hit.hit():
			missed += 1
		elif hit.edge_id != int(edge.get("id", -1)):
			# A tie is legitimate where two edges share a vertex, so only count
			# it wrong when the winner is genuinely further from the point.
			if hit.distance > 0.5:
				wrong += 1
				if first.is_empty():
					first = (
						"edge %d's midpoint resolved to edge %d at %.2f m"
						% [int(edge.get("id", -1)), hit.edge_id, hit.distance]
					)
	if missed > 0:
		problems.append("%d drivable edge midpoints resolved to nothing" % missed)
	if wrong > 0:
		problems.append("%d midpoints resolved to a different edge — %s" % [wrong, first])

	# --- a miss is a miss --------------------------------------------------
	if graph.nearest_edge(FAR_AWAY).hit():
		problems.append("a query 5 km outside the region still found a road")

	# --- the lane centre is off the centreline -----------------------------
	#
	# The seam between opposed carriageway ribbons is the one place a wheel must
	# not land, so a lane centre that coincides with the centreline is a silent
	# return to the bug `P0-5` hit. Checked on a real edge rather than argued.
	problems.append_array(_check_lanes(graph, edges))

	# --- P2-2: a query fits inside a frame ---------------------------------
	problems.append_array(_check_query_time(graph, bounds, edges))

	if problems.is_empty():
		print(
			(
				"  road graph: %d edges, %d drivable, %d indexed segments, %d Q13 probes"
				% [graph.edge_count(), drivable.size(), graph.indexed_segment_count(), probes]
			)
		)
	return problems


## `P2-2`'s last acceptance criterion: nearest-edge is sub-millisecond.
##
## **Timed over a lattice covering the whole region, not along the road.** The
## two are different costs and only the worse one is the budget: a query on a
## centreline is won in the first ring, while a query in the middle of a block
## finds nothing near it and expands rings until the radius bound stops it. A
## road-only probe would measure the easy half and report it as the answer, so
## the misses are here on purpose and are counted separately.
##
## **Asserted on p99 rather than on the maximum.** Every sample carries two
## `Time.get_ticks_usec()` calls and whatever the OS did during the query, so a
## lone outlier is a fact about the machine; a p99 over thousands of probes is a
## fact about the code. The maximum is printed anyway — it costs nothing and a
## pathological one is worth seeing — but it is not the gate.
##
## The measurement is pessimistic by construction, which is the direction that
## matters: the timer calls are charged to the query, so overhead can only make
## a fast query look slow and never the reverse.
##
## ⚠️ **This is the acceptance criterion, not a regression alarm.** Measured by
## disabling `nearest_edge`'s ring early-exit: on-road p50 went 5 -> 56 us and
## p99 10 -> 117 us, an order of magnitude, and the budget never noticed because
## 117 us is still comfortably sub-millisecond. Catching that needs the printed
## distribution to be compared against the baseline in `PROGRESS.md` by someone
## reading it. Tightening the budget to make it fail would be inventing a
## requirement `P2-2` never set.
func _check_query_time(graph: RoadGraph, bounds: AABB, edges: Array) -> PackedStringArray:
	var problems: PackedStringArray = []

	var lattice: PackedVector3Array = _lattice(bounds)
	var on_road: PackedVector3Array = _midpoints(edges)
	if lattice.size() < WARMUP_PROBES or on_road.is_empty():
		problems.append(
			(
				"too few probes to time: %d over the region, %d on the road"
				% [lattice.size(), on_road.size()]
			)
		)
		return problems

	# Discarded on purpose. Without it the first sample carries the allocation of
	# every `Hit` and `Array[Vector2i]` the query path touches, which lands in the
	# maximum and reads as a pathological query.
	for index: int in WARMUP_PROBES:
		graph.nearest_edge(lattice[index])

	problems.append_array(_time_queries(graph, "whole region", lattice))
	problems.append_array(_time_queries(graph, "on the road", on_road))
	return problems


## Time one probe population and report its distribution, failing on p99.
func _time_queries(
	graph: RoadGraph, label: String, points: PackedVector3Array
) -> PackedStringArray:
	var problems: PackedStringArray = []
	var samples := PackedFloat32Array()
	samples.resize(points.size())
	var hits: int = 0
	for index: int in points.size():
		var started: int = Time.get_ticks_usec()
		var hit: RoadGraph.Hit = graph.nearest_edge(points[index])
		samples[index] = float(Time.get_ticks_usec() - started)
		if hit.hit():
			hits += 1
	samples.sort()

	var p99: float = _percentile(samples, 0.99)
	print(
		(
			"  query time (%s): n=%d, %d hit — p50 %.1f us, p99 %.1f us, max %.1f us"
			% [
				label,
				samples.size(),
				hits,
				_percentile(samples, 0.5),
				p99,
				samples[samples.size() - 1],
			]
		)
	)
	if p99 > QUERY_BUDGET_USEC:
		problems.append(
			(
				"nearest_edge p99 is %.1f us over the %s, above the %.0f us budget"
				% [p99, label, QUERY_BUDGET_USEC]
			)
		)
	return problems


## A plan lattice over the region — every place in it a car could be asked about.
##
## `bounds` is the manifest's, so it is the union of everything the region
## contains rather than the declared rectangle. Height is irrelevant: every
## distance in `RoadGraph` is plan-measured.
func _lattice(bounds: AABB) -> PackedVector3Array:
	var points := PackedVector3Array()
	var columns: int = maxi(1, int(bounds.size.x / PROBE_SPACING_M))
	var rows: int = maxi(1, int(bounds.size.z / PROBE_SPACING_M))
	for row: int in rows + 1:
		for column: int in columns + 1:
			(
				points
				. append(
					Vector3(
						bounds.position.x + float(column) * PROBE_SPACING_M,
						0.0,
						bounds.position.z + float(row) * PROBE_SPACING_M,
					)
				)
			)
	return points


## Midpoint of every drivable edge — where the car actually asks from.
func _midpoints(edges: Array) -> PackedVector3Array:
	var points := PackedVector3Array()
	for edge: Dictionary in edges:
		if int(edge.get("elevation_level", 0)) != 0:
			continue
		var polyline: Array = edge.get("polyline", [])
		if polyline.size() < 2:
			continue
		var mid: Array = polyline[floori(polyline.size() / 2.0)]
		points.append(Vector3(mid[0], mid[1], mid[2]))
	return points


## Value at `fraction` through an ascending sample.
static func _percentile(sorted_samples: PackedFloat32Array, fraction: float) -> float:
	if sorted_samples.is_empty():
		return 0.0
	var last: int = sorted_samples.size() - 1
	return sorted_samples[clampi(int(fraction * float(last) + 0.5), 0, last)]


func _check_lanes(graph: RoadGraph, edges: Array) -> PackedStringArray:
	var problems: PackedStringArray = []

	# The formula, independent of any edge: a two-lane 6.4 m road puts the
	# nearside centre 1.6 m off the centreline. Written out so a change to
	# `lane_offset` has to change this number too.
	var offset: float = RoadGraph.lane_offset(6.4, 2)
	if absf(offset - 1.6) > 0.001:
		problems.append("lane_offset(6.4, 2) is %.3f m, expected 1.600 m" % offset)
	if RoadGraph.lane_offset(6.4, 1) != 0.0:
		problems.append("a single-lane road's nearside centre is its centreline")

	# The published table is the whole reason the lane centre is right, so its
	# absence is a failure rather than a fallback. `RoadGraph` degrades to the
	# authored width when it is missing, which is 0.96 m short on a two-lane
	# street — a wrong answer that looks like a right one.
	if not graph.has_carriageway_widths():
		problems.append(
			(
				"city.json published no carriageway widths — lane centres would fall back "
				+ "to the authored street width"
			)
		)
		return problems

	var checked: int = 0
	for edge: Dictionary in edges:
		if int(edge.get("elevation_level", 0)) != 0 or checked >= 50:
			continue
		var points: Array = edge.get("polyline", [])
		if points.size() < 2 or int(edge.get("lanes", 2)) < 2:
			continue
		var mid: Array = points[floori(points.size() / 2.0)]
		var hit: RoadGraph.Hit = graph.nearest_edge(Vector3(mid[0], mid[1], mid[2]))
		if not hit.hit():
			continue
		checked += 1

		# The claim under test: the lane centre comes off the *drawn* carriageway,
		# not the authored width the graph publishes. On a two-lane street those
		# differ by a quarter of the widening.
		var edge_id: int = int(edge.get("id", -1))
		var lanes: int = int(edge.get("lanes", 2))
		var expected: float = RoadGraph.lane_offset(graph.drawn_half_width_of(edge_id) * 2.0, lanes)
		var actual: float = hit.lane_centre.distance_to(hit.point)
		if absf(actual - expected) > 0.01:
			problems.append(
				(
					(
						"edge %d's lane centre is %.3f m off the centreline, expected %.3f m "
						+ "from its drawn half-width of %.3f m"
					)
					% [edge_id, actual, expected, graph.drawn_half_width_of(edge_id)]
				)
			)
			break
		if graph.drawn_half_width_of(edge_id) <= graph.width_of(edge_id) * 0.5:
			problems.append(
				(
					(
						"edge %d's drawn half-width %.3f m is not wider than half its "
						+ "authored width %.3f m — the widening did not travel"
					)
					% [edge_id, graph.drawn_half_width_of(edge_id), graph.width_of(edge_id) * 0.5]
				)
			)
			break

		if hit.lane_centre.distance_to(hit.point) < 0.5:
			problems.append(
				"edge %d's lane centre sits on the centreline" % int(edge.get("id", -1))
			)
			break
		# Left of travel, because Hong Kong drives on the left. The cross product
		# is the whole claim, so it is asserted rather than assumed.
		var to_lane: Vector3 = (hit.lane_centre - hit.point).normalized()
		if to_lane.dot(Vector3.UP.cross(hit.forward).normalized()) < 0.99:
			problems.append("edge %d's lane centre is not left of travel" % int(edge.get("id", -1)))
			break
		if not is_finite(hit.forward.length()) or absf(hit.forward.length() - 1.0) > 0.001:
			problems.append("edge %d's travel direction is not a unit vector" % int(edge.get("id")))
			break

	if checked == 0:
		problems.append("no multi-lane drivable edge was available to check lane placement")
	return problems
