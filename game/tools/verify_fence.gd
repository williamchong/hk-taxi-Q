## Checks `fence.json` against the prop it names and the graph it fences (`P3-29`).
##
##     godot --headless --path game --script res://tools/verify_fence.gd
##
## `Q19`'s acceptance criterion is that a refusal the player cannot see is not
## acceptable. That has two halves and they fail in opposite directions:
##
## - **The refusal without the barrier** — `RoadGraph.fits_car` closes an edge
##   and nothing stands there. This is the invisible wall `Q19` exists to
##   remove.
## - **The barrier without the refusal** — a barrier across a street the player
##   is allowed down. That is a wall nobody asked for.
##
## Both live in `_check_against_the_graph`, because both are the same join
## between the fence document and the predicate, read in opposite directions.
##
## 🔴 **And the collider, which is the whole point of the prop.** Every
## generated railing class is deliberately collider-free — `verify_railings.gd`
## asserts exactly that — so this tool asserts the opposite for a thing that
## sounds like one of them. A barrier the car drives through renders perfectly
## and refuses nothing, which is the invisible wall back again with a picture
## over it.
##
## ⚠️ **What this cannot see is a frame.** The barrier's *legibility* — is it
## readable before it is hit, at speed, from every approach — is `Q62`'s class of
## question and no counter answers it. The evidence is an A/B render at a fixed
## camera plus a drive down each fenced approach.
extends SceneTree

const GeneratedFence = preload("res://scripts/city/generated_fence.gd")
const Manifest = preload("res://scripts/city/city_manifest.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")
const GeneratedRoadGraph = preload("res://scripts/city/generated_road_graph.gd")

## The prop's own ceiling, mirrored from `etl/tests/test_make_barrier.py`, which
## grades the generator where this grades the shipped import.
const TRIANGLE_BUDGET: int = 600

## How far outside `bounds_game` a barrier may stand. A mouth sits inside the
## region by construction — it is a node on a published edge — so the honest
## slack is the row's own reach: half a span of units swung about the mouth,
## which on the widest mouth here (10.24 m, six 2 m units) is 6 m of half-row
## before the prop's own 1 m half-width. Rounded down to 5 m because `bounds_game`
## is the union of *content* and already covers the ribbon each mouth sits on.
## Real placement failures — a dropped offset, a transposed basis — miss by tens
## to hundreds of metres, so the slack costs the check nothing it was catching.
const PLACEMENT_ALLOWANCE_M: float = 5.0


func _init() -> void:
	var manifest: Manifest = Manifest.load_manifest()
	if manifest == null:
		quit(1)
		return
	var document: Dictionary = GeneratedFence.load_fence(manifest.fence_path)
	if document.is_empty():
		quit(1)
		return

	var problems: PackedStringArray = _check(manifest, document)
	for problem: String in problems:
		printerr("  FAIL  ", problem)
	if problems.is_empty():
		print("  ok    ", GeneratedFence.PATH)
	quit(1 if not problems.is_empty() else 0)


func _check(manifest: Manifest, document: Dictionary) -> PackedStringArray:
	var problems: PackedStringArray = []

	# ⚠️ That the manifest and the locator name the same **existing** file is
	# `verify_city.gd`'s check, with the other four documents —
	# `verify_landmarks.gd` states the same division of labour. A local copy here
	# had the path half and not the existence half, which is the weaker of the two.
	var barriers: Array = document.get("barriers", []) as Array
	var fenced: Array = document.get("fenced_edges", []) as Array
	# 🔴 **A second closed population, read separately on purpose (`Q103`).**
	# `fenced_edges` is what `RoadGraph.fenced_edge_ids` re-derives from the car
	# bar; these are off-grade edges closed because nothing *grades* them, not
	# because they are narrow. Pooling the two here would defeat the join below.
	var touchdowns: Array = document.get("touchdown_edges", []) as Array

	problems.append_array(_check_the_prop(document, barriers.size()))
	problems.append_array(_check_placements(manifest, barriers))
	problems.append_array(_check_against_the_graph(manifest, fenced, touchdowns, barriers))

	if problems.is_empty():
		print(
			(
				"  fence: %d barriers at %d mouths over %d edges, %d ends behind another fence"
				% [
					barriers.size(),
					int(document.get("mouths", 0)),
					fenced.size(),
					int(document.get("ends_behind_another_fence", 0))
				]
			)
		)
		# ⚠️ Re-typed to int for the print: JSON has one number type, so the
		# levels arrive as floats and would read "level(s) [-1.0, 1.0]".
		var levels: PackedInt32Array = PackedInt32Array()
		for level: float in document.get("touchdown_levels", []) as Array:
			levels.append(int(level))
		print(
			(
				"  fence: %d touchdown ends dressed of %d seen, over %d off-grade edges at level(s) %s"
				% [
					(
						int(document.get("touchdowns", 0))
						- int(document.get("touchdowns_no_width", 0))
					),
					int(document.get("touchdowns", 0)),
					touchdowns.size(),
					str(levels)
				]
			)
		)
	return problems


## The committed prop: it loads, it is inside its budget, and 🔴 **it collides**.
func _check_the_prop(document: Dictionary, placements: int) -> PackedStringArray:
	var problems: PackedStringArray = []
	var asset: String = str(document.get("asset", ""))
	if asset.is_empty():
		# Only a finding when there is something to place: a region with nothing
		# to close names nothing, and that is the honest answer.
		if placements > 0:
			problems.append("%d barriers are placed and the document names no asset" % placements)
		return problems

	var packed := load(asset) as PackedScene
	if packed == null:
		problems.append("%s did not load as a scene" % asset)
		return problems
	var node: Node3D = packed.instantiate()
	var triangles: int = MeshContract.triangles(node)
	var bounds: AABB = MeshContract.bounds(node)
	# `check_collision` rather than `has_collision` for the richer report, the
	# same reason `verify_landmarks.gd` uses it.
	var collision: PackedStringArray = MeshContract.check_collision(node)
	node.free()

	if bounds.size == Vector3.ZERO:
		problems.append("%s carries no mesh to measure" % asset)
		return problems
	if triangles > TRIANGLE_BUDGET:
		problems.append(
			"%s: %d triangles against the %d budget" % [asset, triangles, TRIANGLE_BUDGET]
		)
	for problem: String in collision:
		# 🔴 The inversion of `verify_railings.gd`'s rule. A barrier the car
		# drives through is `Q19`'s invisible wall with a picture over it.
		problems.append("%s: %s" % [asset, problem])
	# Authored standing on the road, continuing below it. A prop authored the
	# other way up places every barrier in the region buried or floating, by the
	# same amount, which reads as a placement bug forever.
	if bounds.position.y >= 0.0:
		problems.append("%s does not continue below y = 0, so it will float on any camber" % asset)
	if bounds.end.y <= 0.0:
		problems.append("%s has no height above y = 0" % asset)
	return problems


## Every placement resolves to a transform, and stands where a barrier can.
func _check_placements(manifest: Manifest, barriers: Array) -> PackedStringArray:
	var problems: PackedStringArray = []
	var unusable: int = 0
	var outside: int = 0
	var first_outside: String = ""
	for entry: Dictionary in barriers:
		var placement: Variant = GeneratedFence.placement_of(entry)
		if placement == null:
			# ⚠️ Counted, not reported per entry: a bundle with a systematic
			# placement fault would print one line per barrier and bury every
			# other finding here.
			unusable += 1
			continue
		var at: Vector3 = (placement as Transform3D).origin
		if not manifest.bounds.grow(PLACEMENT_ALLOWANCE_M).has_point(at):
			outside += 1
			if first_outside.is_empty():
				first_outside = (
					"barrier on edge %d stands at %s, outside the region"
					% [int(entry.get("edge", -1)), at]
				)
	if unusable > 0:
		problems.append("%d of %d barriers have no usable placement" % [unusable, barriers.size()])
	if outside > 0:
		problems.append("%d barriers stand outside the region — %s" % [outside, first_outside])
	return problems


## The two directions the fence can disagree with the graph it dresses.
func _check_against_the_graph(
	manifest: Manifest, fenced: Array, touchdowns: Array, barriers: Array
) -> PackedStringArray:
	var problems: PackedStringArray = []
	var document: Dictionary = GeneratedRoadGraph.load_graph()
	if document.is_empty():
		problems.append("the road graph did not load, so the fence cannot be checked against it")
		return problems
	var graph: RoadGraph = RoadGraph.from_document(document, manifest)

	# 🔴 **Re-derived from the graph, not compared against itself.** The ETL and
	# `RoadGraph.fits_car` read the same two numbers by different code, so this
	# is the join between them; comparing `fenced_edges` to itself would be the
	# tautology `verify_road_graph.gd` refuses at length.
	var expected: PackedInt32Array = graph.fenced_edge_ids()
	var published: Dictionary[int, bool] = {}
	for edge_id: int in fenced:
		published[int(edge_id)] = true
	for edge_id: int in expected:
		if not published.has(edge_id):
			problems.append(
				"edge %d is fenced by the graph and absent from %s" % [edge_id, GeneratedFence.PATH]
			)
	for edge_id: int in published:
		if not expected.has(edge_id):
			problems.append(
				"edge %d is fenced in %s and open in the graph" % [edge_id, GeneratedFence.PATH]
			)

	# 🔴 **The touchdown set must be off-grade and disjoint from the fenced one.**
	# Both directions are falsifiable and both are the mistake worth catching: a
	# level-0 edge here would close a street nobody asked to close, and an edge
	# in both lists is the ETL having swept a ramp into `fenced_edges`, which
	# would tell `fits_car` that a 6.40 m deck is too narrow for a 1.80 m car.
	# ⚠️ Neither is a tautology — the ETL builds the two sets in separate passes
	# with separate filters, so nothing but this asserts they stayed apart.
	var closed: Dictionary[int, bool] = published.duplicate()
	for edge_id: int in touchdowns:
		if published.has(edge_id):
			problems.append(
				(
					"edge %d is published as both fenced and a touchdown (Q103: two populations)"
					% edge_id
				)
			)
		# ⚠️ **Worded for what `level_of` can actually tell us.** It returns 0 both
		# for a genuine level-0 edge and for an id the graph has never heard of
		# (`road_graph.gd`), so "sits at level 0" would be a true failure carrying
		# a false reason whenever the document is stale.
		if graph.level_of(edge_id) == 0:
			problems.append(
				"edge %d is closed as a touchdown and is not off-grade in the graph" % edge_id
			)
		closed[edge_id] = true

	# A barrier may only stand on an edge the graph closes — the second failure
	# direction, a wall nobody asked for.
	var dressed: Dictionary[int, bool] = {}
	for entry: Dictionary in barriers:
		var edge_id: int = int(entry.get("edge", -1))
		# ⚠️ Only the starved half seeds the reachability walk below, which reads
		# over the fenced set alone; a touchdown edge is not in it and would be
		# filtered there anyway, but keeping `dressed` to one population keeps
		# the two checks saying what their names say.
		if published.has(edge_id):
			dressed[edge_id] = true
		if not closed.has(edge_id):
			problems.append("a barrier stands on edge %d, which is not closed" % edge_id)

	# ⚠️ **And the direction that is the whole point.** An edge the graph refuses
	# with nothing standing there is the invisible wall. Not every fenced edge
	# owes a barrier *on itself* — a pocket is closed at its boundary (`Q19`'s
	# `e222`/`e256`) — so what is asserted is that every fenced edge is
	# **reachable through the fenced set** from a dressed one.
	#
	# 🔴 **Reachability, not adjacency.** A one-hop "touches a dressed edge" rule
	# reads the same on today's bundle, where all 14 components are single edges,
	# and gives a false FAIL the moment a component is five edges long: the middle
	# one touches only undressed neighbours and would be reported as an invisible
	# refusal. `CLAUDE.md` warns this population moves, and `Q19`'s own history is
	# that it moved when the carve ran.
	var undressed: Array[int] = _undressed_in_the_fenced_set(document, published, dressed)
	if not undressed.is_empty():
		problems.append(
			(
				"%d fenced edges have no barrier at or beside them — %s (Q19: an invisible refusal)"
				% [undressed.size(), str(undressed)]
			)
		)
	return problems


## Fenced edges no dressed edge can be reached from, walking the fenced set.
##
## One pass to build the node map, then a flood fill from every dressed edge —
## `pipeline/fence.py::_components` does the same walk on the other side of the
## contract, and this is the reachability half of it.
func _undressed_in_the_fenced_set(
	document: Dictionary, published: Dictionary, dressed: Dictionary
) -> Array[int]:
	var ends: Dictionary[int, Array] = {}
	var at_node: Dictionary[int, Array] = {}
	for edge: Dictionary in document.get("edges", []) as Array:
		var edge_id: int = int(edge.get("id", -1))
		if not published.has(edge_id):
			continue
		var nodes: Array = [int(edge.get("from", -1)), int(edge.get("to", -1))]
		ends[edge_id] = nodes
		for node: int in nodes:
			if not at_node.has(node):
				at_node[node] = []
			at_node[node].append(edge_id)

	var reached: Dictionary[int, bool] = {}
	var frontier: Array[int] = []
	for edge_id: int in dressed:
		if ends.has(edge_id):
			reached[edge_id] = true
			frontier.append(edge_id)
	while not frontier.is_empty():
		for node: int in ends[frontier.pop_back()]:
			for other: int in at_node.get(node, []):
				if not reached.has(other):
					reached[other] = true
					frontier.append(other)

	var undressed: Array[int] = []
	for edge_id: int in published:
		if not reached.has(edge_id):
			undressed.append(edge_id)
	return undressed
