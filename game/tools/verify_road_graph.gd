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

## The `kerbside` vocabulary schema 4 publishes. Spelled out rather than
## compared as literals because `P3-3`'s traffic and `P3-9a`'s fares are the
## consumers to come, and four bare strings in a checker is how the reader and
## the writer end up disagreeing about one of them.
const KERB_NEAR: StringName = &"near"
const KERB_OFF: StringName = &"off"
const KERB_SINGLE: StringName = &"single"
const KERB_DOUBLE: StringName = &"double"

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

	var graph: RoadGraph = RoadGraph.from_document(document, manifest)
	var problems: PackedStringArray = _check(graph, document, manifest)
	for problem: String in problems:
		printerr("  FAIL  ", problem)
	if problems.is_empty():
		print("  ok    ", GeneratedRoadGraph.PATH)
	quit(1 if not problems.is_empty() else 0)


func _check(graph: RoadGraph, document: Dictionary, manifest: CityManifest) -> PackedStringArray:
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

	# --- Q23: the width follows the structure, part-way along an edge -------
	problems.append_array(_check_structure_width(graph, edges))

	# --- Q51: passability is expressed, and not enforced --------------------
	problems.append_array(_check_clearance(graph, edges, manifest))

	# --- Q19: the player's fence is a second bar, not a retuned first one ---
	problems.append_array(_check_car_bar(graph, edges, manifest))

	# --- Q54: the kerbside restrictions are well formed ---------------------
	problems.append_array(_check_kerbside(edges))

	# --- P2-2: a query fits inside a frame ---------------------------------
	problems.append_array(_check_query_time(graph, manifest.bounds, edges))

	if problems.is_empty():
		print(
			(
				"  road graph: %d edges, %d drivable, %d indexed segments, %d Q13 probes"
				% [graph.edge_count(), drivable.size(), graph.indexed_segment_count(), probes]
			)
		)
		print(
			(
				"  clearance: %d drivable edges keep under one lane (%.2f m) clear"
				% [graph.impassable_edge_ids().size(), graph.lane_width_m()]
			)
		)
		print(
			(
				"  fence: %d of those keep under the car's own %.2f m"
				% [graph.fenced_edge_ids().size(), graph.car_width_m()]
			)
		)
	return problems


## `Q54`: the no-stopping runs schema 4 publishes say something a consumer can act on.
##
## Nothing in the engine reads them yet — the marking shader takes the extent off
## the road mesh, and `P3-3`'s traffic and `P3-9a`'s fares are the consumers to
## come — so this is the only thing standing between a malformed join and a
## build that looks fine. Every failure here is one a reader would otherwise hit
## as a wrong answer rather than as an error: a range running off the end of its
## polyline, two runs claiming the same metre of one kerb, or a vocabulary the
## reader has no case for.
##
## The emptiness check is the one that earns its place. A join that stopped
## finding anything publishes a document that parses, validates and draws — and
## the region has 650 restricted edge sides, so zero is not a quiet region.
func _check_kerbside(edges: Array) -> PackedStringArray:
	var problems: PackedStringArray = PackedStringArray()
	var runs: int = 0
	var metres: float = 0.0
	var last: Dictionary = {}

	for edge: Dictionary in edges:
		var published: Array = edge.get("kerbside", [])
		if published.is_empty():
			continue
		var id: int = int(edge.get("id", -1))
		var points: Array = edge.get("polyline", [])
		var length: float = 0.0
		for index: int in range(1, points.size()):
			length += RoadGraph.plan_distance(
				Vector3(points[index - 1][0], points[index - 1][1], points[index - 1][2]),
				Vector3(points[index][0], points[index][1], points[index][2])
			)

		last.clear()
		for run: Dictionary in published:
			runs += 1
			var side: String = str(run.get("side", ""))
			var kind: String = str(run.get("kind", ""))
			var from_m: float = float(run.get("from_m", -1.0))
			var to_m: float = float(run.get("to_m", -1.0))
			metres += to_m - from_m

			if side != KERB_NEAR and side != KERB_OFF:
				problems.append("edge %d has a kerbside run on side '%s'" % [id, side])
			if kind != KERB_SINGLE and kind != KERB_DOUBLE:
				problems.append("edge %d has a kerbside run of kind '%s'" % [id, kind])
			if from_m < 0.0 or to_m <= from_m or to_m > length + 1.0:
				problems.append(
					(
						"edge %d has a kerbside run %.2f-%.2f m on a %.2f m polyline"
						% [id, from_m, to_m, length]
					)
				)
			# Ordered and disjoint per side, which is what lets a consumer stop
			# at the first run covering a position rather than scan them all.
			if last.has(side) and from_m < float(last[side]):
				problems.append(
					"edge %d has overlapping or unordered %s runs at %.2f m" % [id, side, from_m]
				)
			last[side] = to_m

	if runs == 0:
		problems.append(
			"no edge carries a kerbside run; the NSR join found nothing, or stopped running"
		)
	elif problems.is_empty():
		print("  kerbside: %d no-stopping runs over %.0f m of kerb" % [runs, metres])
	return problems


## `Q23`: a level-0 edge that climbs onto a ramp is narrow there and wide later.
##
## The case `_check_lanes` cannot reach. It samples the midpoint of the first 50
## level-0 edges, and the 16 edges this is about are neither early in the
## document nor on structure at their middle — so every assertion there would go
## on passing if the per-station width were quietly collapsed back to one number
## per edge. This finds an edge that is genuinely mixed and asserts both ends.
##
## Refuses to pass vacuously: a build with no mixed edge at all is reported,
## because "the case never came up" and "the case works" are the same green.
func _check_structure_width(graph: RoadGraph, edges: Array) -> PackedStringArray:
	var problems: PackedStringArray = PackedStringArray()
	var examined: int = 0
	# Mixed edges the floor actually lifted off structure. See the assertion at
	# the foot of the loop for why a count is needed beside "never narrower".
	var tapered: int = 0

	for edge: Dictionary in edges:
		if int(edge.get("elevation_level", 0)) != 0:
			continue
		var flags: Array = edge.get("on_structure", [])
		var points: Array = edge.get("polyline", [])
		if flags.size() != points.size() or points.size() < 2:
			continue
		# The first flagged station, and the unflagged one **furthest from any**
		# of them. Not simply the last unflagged one: `surface.py` tapers the
		# width over ~15 m of the approach, so a station just past the flag is
		# legitimately mid-taper and neither narrow nor fully widened. Taking the
		# far end is the only place the at-grade width is certain to have
		# arrived.
		var on: int = -1
		var off: int = -1
		var furthest: int = -1
		for station: int in flags.size():
			if bool(flags[station]):
				if on < 0:
					on = station
				continue
			var span: int = flags.size()
			for other: int in flags.size():
				if bool(flags[other]):
					span = mini(span, absi(station - other))
			if span > furthest:
				furthest = span
				off = station
		# Both, or there is nothing mixed here to check.
		if on < 0 or off < 0:
			continue
		examined += 1

		var edge_id: int = int(edge.get("id", -1))
		var authored_half: float = graph.width_of(edge_id) * 0.5
		var on_deck: float = graph.drawn_half_width_of(edge_id, on)
		var on_street: float = graph.drawn_half_width_of(edge_id, off)

		# On the deck the ribbon is drawn at the authored street width — a
		# viaduct ends at a parapet, and widening it hangs the carriageway over
		# air. That is the whole of `Q23`.
		if absf(on_deck - authored_half) > 0.01:
			problems.append(
				(
					(
						"edge %d is on structure at station %d but drawn %.3f m wide, not its "
						+ "authored %.3f m — the widening did not stop at the bridge"
					)
					% [edge_id, on, on_deck, authored_half]
				)
			)
			break
		# And off it the ribbon is never NARROWER than the street it covers.
		#
		# 🔴 **Not-narrower since `Q94`, where it used to be strictly wider —
		# `_check_lanes`'s inversion, arriving here a release late.** `Q95` made
		# the widening a floor, so an edge whose own carriageway reaches the
		# floor is drawn at its own width and the two are equal off structure as
		# well as on it. That became reachable when a third publisher licensed
		# `e522` at **10.232 m** against a 10.24 m floor: 4 mm of lift, inside
		# this test's own tolerance, reported as "the widening was lost". The
		# widening was not lost; there was nothing to lift.
		if on_street < authored_half - 0.001:
			problems.append(
				(
					(
						"edge %d is off structure at station %d and drawn %.3f m, NARROWER than "
						+ "its authored %.3f m — the ribbon does not cover the road it publishes"
					)
					% [edge_id, off, on_street, authored_half]
				)
			)
			break
		# ⚠️ **The positive half, and it is here because the test above had to be
		# weakened to allow the equal case** — `_check_lanes` carries the same
		# pair for the same reason. "Never narrower" is satisfied by a ribbon
		# that merely echoes the graph, which is exactly what the strict test
		# used to catch, so something still has to show the floor travels on a
		# mixed edge. Asserted below over every edge examined, not per edge.
		if on_street > authored_half + 0.01:
			tapered += 1

	if examined > 0 and tapered == 0:
		problems.append(
			(
				(
					"no mixed edge is drawn wider off structure than its authored width across "
					+ "%d examined — the carriageway floor did not travel across a taper"
				)
				% examined
			)
		)
	if examined == 0:
		problems.append(
			(
				"no level-0 edge is on structure for part of its length, so Q23's per-station "
				+ "width was never exercised — check roadgraph.json carries on_structure"
			)
		)
	elif problems.is_empty():
		print("  Q23: %d level-0 edges narrow where they stand on structure" % examined)
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

	var lattice: PackedVector3Array = PlanLattice.over(bounds, PROBE_SPACING_M)
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
	# At-grade edges the floor actually lifted. Asserted non-zero below, because
	# a "never narrower" test alone passes on a table that echoes the graph.
	var widened: int = 0
	for edge: Dictionary in edges:
		if int(edge.get("elevation_level", 0)) != 0 or checked >= 50:
			continue
		var points: Array = edge.get("polyline", [])
		if points.size() < 2 or int(edge.get("lanes", 2)) < 2:
			continue
		# The station is sampled as well as the point, because since `Q23` the
		# drawn width varies along an edge and "the drawn half-width" is not a
		# question you can ask without saying where.
		var station: int = floori(points.size() / 2.0)
		var mid: Array = points[station]
		var hit: RoadGraph.Hit = graph.nearest_edge(Vector3(mid[0], mid[1], mid[2]))
		if not hit.hit():
			continue
		checked += 1

		# The claim under test: the lane centre comes off the *drawn* carriageway,
		# not the authored width the graph publishes. On a two-lane street those
		# differ by a quarter of the widening.
		var edge_id: int = int(edge.get("id", -1))
		var lanes: int = int(edge.get("lanes", 2))
		var drawn_half: float = graph.drawn_half_width_of(edge_id, station)
		var expected: float = RoadGraph.lane_offset(drawn_half * 2.0, lanes)
		var actual: float = hit.lane_centre.distance_to(hit.point)
		if absf(actual - expected) > 0.01:
			problems.append(
				(
					(
						"edge %d's lane centre is %.3f m off the centreline, expected %.3f m "
						+ "from its drawn half-width of %.3f m at station %d"
					)
					% [edge_id, actual, expected, drawn_half, station]
				)
			)
			break
		# ⚠️ Conditional since `Q23`, and 🔴 **NOT-NARROWER since `Q95`, where it
		# used to be strictly wider.** The widening became a floor —
		# `max(width_m, floor)` — rather than a multiplier, so an edge whose
		# *measured* carriageway already exceeds the floor is drawn at exactly
		# its own width and the two are equal at grade. Asserting "wider" there
		# is asserting the multiplier, and it failed on `e10` TUNG LO WAN ROAD,
		# an 11.9 m street the survey measured. What survives, and is the claim
		# that actually matters, is that the ribbon is never drawn *narrower*
		# than the road the graph publishes. On structure the two are equal for
		# the older reason: a deck ends at a parapet, so its floor is 0.0 m.
		var flags: Array = edge.get("on_structure", [])
		var on_structure: bool = station < flags.size() and bool(flags[station])
		if not on_structure and drawn_half > graph.width_of(edge_id) * 0.5 + 0.001:
			widened += 1
		if drawn_half < graph.width_of(edge_id) * 0.5 - 0.001:
			problems.append(
				(
					(
						"edge %d's drawn half-width %.3f m is NARROWER than half its "
						+ "authored width %.3f m at station %d (on structure: %s) — "
						+ "the ribbon does not cover the road it publishes"
					)
					% [edge_id, drawn_half, graph.width_of(edge_id) * 0.5, station, on_structure]
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
	# 🔴 **The positive half of the floor claim, and it is here because the test
	# above had to be weakened to allow it** (`Q95`). "Never narrower" can be
	# satisfied by a drawn half-width that simply echoes the authored one, which
	# is exactly the failure the strict "wider" test used to catch — so something
	# still has to show the floor travels. Most of the region is authored 6.4 m
	# under a 10.24 m floor, so *some* at-grade edge must come back wider; zero
	# means the drawn table has stopped being read.
	if widened == 0:
		problems.append(
			(
				(
					"no at-grade edge is drawn wider than its authored width across %d checked — "
					+ "the carriageway floor did not travel"
				)
				% checked
			)
		)
	problems.append_array(_check_lane_source(edges))
	return problems


## 🔴 **The one thing about the lane COUNT this file can check, and it needs
## saying why the rest of `_check_lanes` is not it.**
##
## Every assertion above re-derives its expectation from the same `lanes` it
## read out of the edge dictionary, so a count that is simply wrong satisfies
## all of them — they grade the width plumbing. Since `Q94` the count is a
## *reading* on part of the region rather than authored policy throughout, and
## a derivation that silently fell back to authored everywhere would leave this
## whole function green. `widened` exists against the same weakness and `Q95`
## records why it had to.
##
## ⚠️ **Conditional on the width survey having run**, not asserted outright: a
## city whose file transcribes no design manual measures nothing and publishes
## an authored count everywhere, which is correct rather than broken. What
## cannot be true is a region with measured *widths* and no measured count
## anywhere — TD's through-lane range resolves over half of them.
func _check_lane_source(edges: Array) -> PackedStringArray:
	var problems: PackedStringArray = []
	var measured_widths: int = 0
	var measured_lanes: int = 0
	var unattributed: int = 0
	var lanes_without_width: int = 0
	for edge: Dictionary in edges:
		var width_source: String = str(edge.get("width_source", "authored"))
		var lanes_source: String = str(edge.get("lanes_source", "authored"))
		var publisher: String = str(edge.get("width_publisher", ""))
		if width_source != "authored":
			measured_widths += 1
		if lanes_source != "authored":
			measured_lanes += 1
		# 🔴 **A measured width names the publishers that read it, and an
		# authored one names none.** Since `Q94` the three publishers do not
		# measure the same quantity — HyD reads the trafficable carriageway
		# where the two line sources read kerb to kerb — so a width with no
		# publisher beside it is a width whose meaning cannot be recovered.
		if (width_source == "authored") != publisher.is_empty():
			unattributed += 1
		# 🔴 **A lane count is bracketed off a MEASURED width.** One standing on
		# an authored 6.4 m would be the speed-limit table laundered into a
		# reading — the exact move `Q95` was opened about — and nothing else in
		# the bundle can see it: every counter would close and every frame would
		# render.
		if lanes_source != "authored" and width_source == "authored":
			lanes_without_width += 1
	if unattributed > 0:
		problems.append(
			(
				(
					"%d edges disagree about whether their width was measured — `width_source` "
					+ "and `width_publisher` must be authored-and-empty or neither"
				)
				% unattributed
			)
		)
	if lanes_without_width > 0:
		problems.append(
			(
				(
					"%d edges carry a measured lane count over an AUTHORED width — the bracket "
					+ "read the speed-limit table and called it a measurement"
				)
				% lanes_without_width
			)
		)
	if measured_widths > 0 and measured_lanes == 0:
		problems.append(
			(
				(
					"%d edges carry a measured width and not one carries a measured lane "
					+ "count — the bracket did not travel"
				)
				% measured_widths
			)
		)
	return problems


## `Q51`: the graph knows which edges a car cannot fit down, and says so without
## refusing them.
##
## Three separate claims, because they fail in different directions:
##
## 1. **Every edge carries a measurement.** An edge with no clearance array reads
##    as unknown, and unknown reads as passable — so a table covering 796 of 797
##    edges routes traffic into the 797th and nothing says a word.
## 2. **`is_routable` differs from `is_drivable` on exactly the blocked set.**
##    The predicate `P3-3` will route on, checked against the set the overlay
##    paints, so the two cannot drift apart.
## 3. **`nearest_edge` still answers on a blocked edge.** This is the whole of
##    `Q51`'s decision and the half a later change is most likely to undo: it is
##    tempting to reuse `Q13`'s refusal here, and it would blank the road name
##    and the lane centre exactly where the player is stuck against a wall.
##
## Refuses to pass vacuously, and deliberately **not** by requiring the blocked
## set to be non-empty: a build that finally clears all 26 has to pass. What is
## asserted instead is that the measurement ran — that some station reads
## narrower than the carriageway drawn over it.
func _check_clearance(graph: RoadGraph, edges: Array, manifest: CityManifest) -> PackedStringArray:
	var problems: PackedStringArray = PackedStringArray()
	if not graph.has_clearances():
		problems.append("some edges carry no clearance measurement; unknown reads as passable")
		return problems

	var narrowed: int = 0
	for edge: Dictionary in edges:
		var edge_id: int = int(edge.get("id", -1))
		if not graph.is_drivable(edge_id):
			continue
		var stations: int = graph.polyline_of(edge_id).size()
		for station: int in stations:
			var clear: float = graph.clear_width_of(edge_id, station)
			if clear == CityManifest.NOT_MEASURED:
				continue
			var drawn: float = graph.drawn_half_width_of(edge_id, station) * 2.0
			if clear > drawn + 0.01:
				problems.append(
					(
						"edge %d station %d keeps %.2f m clear of a %.2f m carriageway"
						% [edge_id, station, clear, drawn]
					)
				)
			elif clear < drawn:
				narrowed += 1
	if narrowed == 0:
		# Every station of every edge reads exactly as wide as the tarmac over
		# it. That is not a clear city, it is an instrument that never fired.
		problems.append("no station anywhere reads narrower than its carriageway")

	var blocked: PackedInt32Array = graph.impassable_edge_ids()
	for edge_id: int in blocked:
		if graph.is_routable(edge_id):
			problems.append("edge %d is impassable and routable at the same time" % edge_id)
		var points: PackedVector3Array = graph.polyline_of(edge_id)
		if points.size() < 2:
			continue
		# On its own centreline, where nothing can be nearer. A miss here means
		# passability has been folded into the index and the player has lost the
		# road under their wheels.
		var hit: RoadGraph.Hit = graph.nearest_edge(points[floori(points.size() / 2.0)])
		if not hit.hit():
			problems.append("edge %d is blocked and nearest_edge no longer finds it" % edge_id)

	# Re-derived from the **manifest's own arrays**, not from
	# `impassable_edge_ids`. That set is built out of `is_passable`, so
	# comparing the two would be a tautology no bug could fail — it says only
	# that a definition equals itself. Reading the published widths straight
	# from `city.json` instead tests what could actually go wrong: the parse,
	# and whether each edge's array landed in the right parallel-array slot.
	for edge: Dictionary in edges:
		var edge_id: int = int(edge.get("id", -1))
		var published: PackedFloat32Array = manifest.carriageway_clear_width_m.get(
			edge_id, PackedFloat32Array()
		)
		var tightest: float = INF
		for width: float in published:
			if width != CityManifest.NOT_MEASURED:
				tightest = minf(tightest, width)
		var expected: bool = graph.is_drivable(edge_id) and tightest >= manifest.lane_width_m
		if graph.is_routable(edge_id) != expected:
			problems.append(
				(
					"edge %d reads %s from the graph and %s from %s"
					% [edge_id, graph.is_routable(edge_id), expected, CityManifest.PATH]
				)
			)
	return problems


## The player's fence is a **second** bar over the same measurement (`Q19`).
##
## Four claims, and the third is the one a later change is most likely to undo:
##
## 1. **Both bars are published.** A fence with no bar leaves every edge open,
##    which is the honest fallback but not a shipped state — so a bundle that
##    names a clearance table and no car width is a finding.
## 2. **The fence agrees with the published widths.** Re-derived from the
##    manifest's own arrays, never from `fenced_edge_ids`, for the reason
##    `_check_clearance` gives at length: comparing a set built out of
##    `fits_car` against `fits_car` is a tautology no bug could fail.
## 3. **The two bars have not been merged.** `is_passable` must still read the
##    lane and `fits_car` the car. `Q19` forbids merging them in either
##    direction: at the car's bar the router is sent down `e207`'s 1.95 m, at
##    the lane's the player is fenced out of road that fits. The bar *ordering*
##    is asserted; how many edges fall between the bars is **printed, not
##    asserted**, because a region could honestly have none and failing the
##    build on a fact about Hong Kong is a finding turned into a bar.
##
## ⚠️ **What is deliberately NOT here**: "a fenced edge must not be routable".
## The guard below returns early unless `car_width_m < lane_width_m`, so
## `fenced` already implies `not is_passable` implies `not is_routable` — that
## test would be proved by the guard rather than by the data, and a check no
## input can fail is `Q72`'s tautology.
##
## Refuses to pass vacuously, and — as in `_check_clearance` — **not** by
## requiring the fence to be non-empty: a build that finally clears every edge
## has to pass. What is asserted instead is that the two bars are different
## numbers in the right order.
func _check_car_bar(graph: RoadGraph, edges: Array, manifest: CityManifest) -> PackedStringArray:
	var problems := PackedStringArray()
	if not graph.has_clearances():
		# Already reported by `_check_clearance`; saying it twice would double
		# every message on a bundle with no measurement at all.
		return problems
	if manifest.car_width_m <= 0.0:
		problems.append(
			(
				"%s names a clearance table but no car_width_m, so nothing is fenced"
				% CityManifest.PATH
			)
		)
		return problems
	if manifest.car_width_m >= manifest.lane_width_m:
		# The order is what makes the fence a subset of the blocked set. Reversed
		# or equal, claims 3 and 4 are unreachable and this whole function passes
		# by construction — `Q72`'s tautology, caught before it can certify.
		problems.append(
			(
				(
					"car_width_m %.2f m is not under lane_width_m %.2f m; the player fence"
					+ " and the routing bar have converged (Q19)"
				)
				% [manifest.car_width_m, manifest.lane_width_m]
			)
		)
		return problems

	var between: int = 0
	for edge: Dictionary in edges:
		var edge_id: int = int(edge.get("id", -1))
		var published: PackedFloat32Array = manifest.carriageway_clear_width_m.get(
			edge_id, PackedFloat32Array()
		)
		var tightest: float = INF
		for width: float in published:
			if width != CityManifest.NOT_MEASURED:
				tightest = minf(tightest, width)
		# ⚠️ Expressed as expected-**fenced** and compared with `!=`, exactly as
		# `_check_clearance` expresses expected-routable. Deriving "fits" and
		# comparing it against "fenced" reads naturally and is wrong on every
		# off-grade edge, where both are false because neither is drivable —
		# which is how this first ran, failing on five flyover edges.
		#
		# `tightest` is `INF` on an edge whose stations were all swallowed by the
		# junction caps, and `INF < bar` is false: unmeasured is unfenced, on
		# `min_clear_width_of`'s own "nothing is known to stand here" terms.
		var expected: bool = graph.is_drivable(edge_id) and tightest < manifest.car_width_m
		var fenced: bool = graph.is_drivable(edge_id) and not graph.fits_car(edge_id)
		if fenced != expected:
			problems.append(
				(
					"edge %d reads fenced=%s from the graph against %s from %s"
					% [edge_id, fenced, expected, CityManifest.PATH]
				)
			)
		if fenced and graph.is_routable(edge_id):
			problems.append(
				(
					"edge %d is fenced against the car and still routable; the bars have crossed"
					% edge_id
				)
			)
		# Claim 3's evidence, counted rather than asserted per edge: an edge
		# wider than the car and narrower than a lane can only exist while the
		# two bars are still two.
		if (
			graph.is_drivable(edge_id)
			and not graph.is_passable(edge_id)
			and graph.fits_car(edge_id)
		):
			between += 1
	# ⚠️ **Printed, never appended.** A region could honestly have no edge between
	# the two bars — that is a fact about Hong Kong, and failing the build on it
	# is a finding turned into a bar. The merge this was written to catch is
	# already caught twice over: by the `car_width_m >= lane_width_m` guard above
	# for a config merge, and by the per-edge re-derivation for a code one, which
	# a mutation pointing `fits_car` at `_lane_width_m` fails by name.
	print(
		(
			"  bars: %d drivable edges blocked at the lane (%.2f m), clear at the car (%.2f m)"
			% [between, manifest.lane_width_m, manifest.car_width_m]
		)
	)
	return problems
