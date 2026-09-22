## Checks the runtime road-graph merge against `pipeline/join.py`'s (`P5-9d`).
##
## The GDScript merge is a rule-for-rule mirror of the Python one, and the
## Python one is the reference: `reachability.py --graph-dir` routes across it,
## and `join.json` records what it did. So this reads the pair the sync listed —
## the first two regions of `regions.json` — through `RoadGraph.merged_inputs`,
## reads `etl/out/<frame>+<other>/` beside the project, and diffs them:
##
## * `join.json`'s counters, every one;
## * every node — position within a millimetre, `kind` exactly;
## * every edge, field by field — its polyline within a millimetre, every other
##   field exactly — and no `(source_id, run)` twice;
## * the turns, in order;
## * the clearance rows, re-keyed through the id map, against `clearance.json`;
## * that every `nearest_edge` and every fence `edge` either region publishes
##   resolves through its id map to an edge the merged graph has.
##
##     godot --headless --path game --script res://tools/verify_join.gd [-- --dump=<dir>]
##
## `--dump=` writes the runtime's merged `roadgraph.json` and `clearance.json`
## there, for `tools/reachability.py --graph-dir` to route across (`P5-9f`).
##
## With one region listed there is nothing to merge and it says so and passes.
## With two and no reference it fails and names the command that writes one —
## a check that skips when its truth is missing is a check nobody reads.
extends SceneTree

const GeneratedRegions = preload("res://scripts/city/generated_regions.gd")
const GeneratedFares = preload("res://scripts/city/generated_fares.gd")
const GeneratedFence = preload("res://scripts/city/generated_fence.gd")
const GeneratedRoadGraph = preload("res://scripts/city/generated_road_graph.gd")
const Manifest = preload("res://scripts/city/city_manifest.gd")
const Graph = preload("res://scripts/city/road_graph.gd")
const CommandLine = preload("res://scripts/core/cmdline.gd")
const MinimapMeshScript = preload("res://scripts/ui/minimap_mesh.gd")
const RouterScript = preload("res://scripts/city/road_router.gd")
const RouterDiff = preload("res://tools/router_diff.gd")

const TOLERANCE_M: float = 0.001
## `P3-43`: a routed pair across the merge against `reachability.py --graph-dir`.
## The same millimetre as one region: the second region's polylines are
## translated by its offset, and a translation moves no length, so the 64-bit
## sums agree as they do at home (measured 0.000000 m over 334,767 pairs).
const ROUTE_TOLERANCE_M: float = 0.001
const REPORT_KEYS: PackedStringArray = [
	"owned_a",
	"owned_b",
	"foreign_matched",
	"foreign_unmatched",
	"nodes",
	"nodes_unified",
	"edges",
	"turns",
	"turns_dropped",
]

var _problems: PackedStringArray = []


func _init() -> void:
	var regions: PackedStringArray = GeneratedRegions.listed()
	if regions.size() < 2:
		print("  SKIP  one region listed in %s — nothing to merge" % GeneratedRegions.PATH)
		quit(0)
		return
	var pair := PackedStringArray([regions[0], regions[1]])
	var out: String = (
		ProjectSettings
		. globalize_path("res://../etl/out/%s+%s" % [pair[0], pair[1]])
		. simplify_path()
	)
	var reference: Dictionary = _read(out.path_join("roadgraph.json"))
	var clearance: Dictionary = _read(out.path_join("clearance.json"))
	var report: Dictionary = _read(out.path_join("join.json"))
	if reference.is_empty() or clearance.is_empty() or report.is_empty():
		printerr(
			(
				(
					"  FAIL  no reference merge at %s. Write it:\n"
					+ "        cd etl && python -m pipeline.join --region-a %s --region-b %s"
				)
				% [out, pair[0], pair[1]]
			)
		)
		quit(1)
		return

	var inputs: Dictionary = Graph.merged_inputs(pair)
	if inputs.has("error"):
		_fail("the runtime merge refused the pair: %s" % inputs["error"])
		_finish(pair)
		return
	var merged: Dictionary = inputs["document"]
	_check_report(inputs["report"], report)
	_check_nodes(merged.get("nodes", []), reference.get("nodes", []))
	_check_edges(merged.get("edges", []), reference.get("edges", []))
	_check_turns(merged.get("turn_restrictions", []), reference.get("turn_restrictions", []))
	_check_clearance(inputs["manifest"], clearance.get("clearance", []))
	var graph: RoadGraph = Graph.resident(pair)
	if graph.edge_count() != (reference.get("edges", []) as Array).size():
		_fail(
			(
				"RoadGraph holds %d edges, the reference %d"
				% [graph.edge_count(), (reference.get("edges", []) as Array).size()]
			)
		)
	_check_documents(graph, pair)
	_check_foreign_aliases(graph, merged, pair)
	_check_minimap(graph, pair)
	_check_router(graph, inputs["manifest"], out, pair)

	var dump: String = CommandLine.value("--dump=")
	if not dump.is_empty():
		_dump(dump, merged, inputs["manifest"], clearance)
	_finish(pair)


func _check_report(ours: Dictionary, theirs: Dictionary) -> void:
	for key: String in REPORT_KEYS:
		if int(ours.get(key, -1)) != int(theirs.get(key, -2)):
			_fail("join.json %s: runtime %s, reference %s" % [key, ours.get(key), theirs.get(key)])
	print(
		(
			"        merge: %d edges over %d nodes, %d unified, %d turns (%d dropped), foreign %d matched / %d unmatched"
			% [
				ours.get("edges"),
				ours.get("nodes"),
				ours.get("nodes_unified"),
				ours.get("turns"),
				ours.get("turns_dropped"),
				ours.get("foreign_matched"),
				ours.get("foreign_unmatched"),
			]
		)
	)


func _check_nodes(ours: Array, theirs: Array) -> void:
	if ours.size() != theirs.size():
		_fail("%d nodes, the reference %d" % [ours.size(), theirs.size()])
		return
	var worst: float = 0.0
	for index: int in ours.size():
		var a: Dictionary = ours[index]
		var b: Dictionary = theirs[index]
		if int(a["id"]) != int(b["id"]) or str(a["kind"]) != str(b["kind"]):
			_fail("node %d: %s against %s" % [index, a, b])
			continue
		worst = maxf(worst, _gap(a["pos"], b["pos"]))
	if worst > TOLERANCE_M:
		_fail("a node position differs by %.4f m" % worst)
	print("        %d nodes, worst position %.4f m" % [ours.size(), worst])


func _check_edges(ours: Array, theirs: Array) -> void:
	if ours.size() != theirs.size():
		_fail("%d edges, the reference %d" % [ours.size(), theirs.size()])
		return
	var identities: Dictionary = {}
	var worst: float = 0.0
	var fields_differing: int = 0
	for index: int in ours.size():
		var a: Dictionary = ours[index]
		var b: Dictionary = theirs[index]
		var key := Vector2i(int(a["source_id"]), int(a["run"]))
		if identities.has(key):
			_fail("(source_id, run) %s appears twice" % key)
		identities[key] = true
		if a.keys().size() != b.keys().size():
			_fail("edge %s carries %s, the reference %s" % [a["id"], a.keys(), b.keys()])
		for field: Variant in b:
			if field == "polyline":
				var pa: Array = a.get("polyline", [])
				var pb: Array = b["polyline"]
				if pa.size() != pb.size():
					_fail(
						(
							"edge %s polyline %d points, the reference %d"
							% [a["id"], pa.size(), pb.size()]
						)
					)
					continue
				for step: int in pa.size():
					worst = maxf(worst, _gap(pa[step], pb[step]))
			elif a.get(field) != b[field]:
				fields_differing += 1
				if fields_differing <= 5:
					_fail(
						"edge %s field %s: %s against %s" % [a["id"], field, a.get(field), b[field]]
					)
	if worst > TOLERANCE_M:
		_fail("a polyline vertex differs by %.4f m" % worst)
	if fields_differing > 5:
		_fail("and %d more fields differ" % (fields_differing - 5))
	print(
		(
			"        %d edges field by field, worst vertex %.4f m, %d duplicate identities"
			% [ours.size(), worst, ours.size() - identities.size()]
		)
	)


func _check_turns(ours: Array, theirs: Array) -> void:
	if ours.size() != theirs.size():
		_fail("%d turns, the reference %d" % [ours.size(), theirs.size()])
		return
	for index: int in ours.size():
		for key: String in ["from_edge", "via_node", "to_edge"]:
			if int(ours[index][key]) != int(theirs[index][key]):
				_fail("turn %d %s: %s against %s" % [index, key, ours[index], theirs[index]])
				break
	print("        %d turns in order" % ours.size())


func _check_clearance(tables: Manifest, rows: Array) -> void:
	var table: Dictionary = tables.carriageway_clear_width_m
	if table.size() != rows.size():
		_fail("%d clearance rows, the reference %d" % [table.size(), rows.size()])
	var worst: float = 0.0
	for row: Dictionary in rows:
		var edge: int = int(row["edge"])
		if not table.has(edge):
			_fail("the reference has clearance for edge %d, the runtime none" % edge)
			continue
		var ours: PackedFloat32Array = table[edge]
		var theirs: Array = row["clear_width_m"]
		if ours.size() != theirs.size():
			_fail(
				(
					"edge %d: %d clearance stations, the reference %d"
					% [edge, ours.size(), theirs.size()]
				)
			)
			continue
		for station: int in ours.size():
			worst = maxf(worst, absf(ours[station] - float(theirs[station])))
	if worst > TOLERANCE_M:
		_fail("a clearance width differs by %.4f m" % worst)
	print("        %d clearance rows re-keyed, worst %.4f m" % [table.size(), worst])


## Every edge id a region's own documents publish resolves to a merged edge.
func _check_documents(graph: RoadGraph, pair: PackedStringArray) -> void:
	var known: Dictionary = {}
	for id: int in graph.edge_ids():
		known[id] = true
	for region: String in pair:
		var fares: Dictionary = GeneratedFares.load_fares(GeneratedFares.path(region))
		var fence: Dictionary = GeneratedFence.load_fence(GeneratedFence.path(region))
		var named: Array[int] = []
		for node: Dictionary in fares.get("nodes", []):
			named.append(int(node.get("nearest_edge", -1)))
		for barrier: Dictionary in fence.get("barriers", []):
			named.append(int(barrier.get("edge", -1)))
		for edge: Variant in fence.get("fenced_edges", []):
			named.append(int(edge))
		var unresolved: int = 0
		for local: int in named:
			if not known.has(graph.edge_id_in(region, local)):
				unresolved += 1
		if unresolved > 0:
			_fail(
				(
					"%s: %d of %d document edge ids resolve to no merged edge"
					% [region, unresolved, named.size()]
				)
			)
		print(
			(
				"        %s: %d fare and fence edge ids resolve through the map"
				% [region, named.size()]
			)
		)


## Every foreign copy either region publishes resolves to its owner's merged
## edge — the same `(source_id, run)`. No shipped fare, fence or turn names a
## foreign id today, so without this the alias could be dropped and every other
## check here would stay green; it was mutation-checked that way.
func _check_foreign_aliases(graph: RoadGraph, merged: Dictionary, pair: PackedStringArray) -> void:
	var identity_of: Dictionary = {}
	for edge: Dictionary in merged.get("edges", []):
		identity_of[int(edge["id"])] = Vector2i(int(edge["source_id"]), int(edge["run"]))
	for region: String in pair:
		var document: Dictionary = GeneratedRoadGraph.load_graph(GeneratedRoadGraph.path(region))
		var copies: Array = document.get("foreign_edges", [])
		var wrong: int = 0
		for copy: Dictionary in copies:
			var id: int = graph.edge_id_in(region, int(copy["id"]))
			var own := Vector2i(int(copy["source_id"]), int(copy["run"]))
			if identity_of.get(id, Vector2i(-1, -1)) != own:
				wrong += 1
		if wrong > 0:
			_fail(
				(
					"%s: %d of %d foreign copies alias no owner of the same run"
					% [region, wrong, copies.size()]
				)
			)
		print("        %s: %d foreign copies alias their owner" % [region, copies.size()])


## The minimap draws ONE mesh from the merged graph, built once (`P3-44`), so
## crossing a region line is only safe while that mesh already reaches across
## it. Asserted on the strokes the map is built from: every drivable merged
## edge is one, and they stand on BOTH sides of the second region's offset —
## a map built from the frame alone stops dead at the line, with no error.
func _check_minimap(graph: RoadGraph, pair: PackedStringArray) -> void:
	var strokes: Array = MinimapMeshScript.strokes_of(graph, 0.0, 0.0)
	var drivable: int = 0
	for edge_id: int in graph.edge_ids():
		if graph.is_drivable(edge_id):
			drivable += 1
	if strokes.size() != drivable:
		_fail("the minimap strokes %d edges of %d drivable" % [strokes.size(), drivable])
	var seam: float = graph.region_offset(pair[1]).x
	var west: int = 0
	var east: int = 0
	for stroke: MinimapMeshScript.Stroke in strokes:
		var middle: Vector2 = stroke.points[stroke.points.size() >> 1]
		if middle.x < seam:
			west += 1
		else:
			east += 1
	if west == 0 or east == 0:
		_fail(
			(
				"the minimap's roads stand on one side of %s's offset (%d west, %d east of x=%.0f)"
				% [pair[1], west, east, seam]
			)
		)
	print(
		(
			"        minimap: %d strokes, %d west and %d east of %s's offset"
			% [strokes.size(), west, east, pair[1]]
		)
	)


## `P3-43`: `RoadRouter` over the runtime merge against `reachability.py`'s
## tables over the reference merge. No id map: both renumber the second region
## from the frame's maximum in document order, and `_check_edges` has already
## asserted `id`, `from` and `to` on every edge.
func _check_router(
	graph: RoadGraph, tables: Manifest, out: String, pair: PackedStringArray
) -> void:
	var path: String = out.path_join("reachability.json")
	var command: String = RouterDiff.reference_command(
		pair[0], "etl/out/%s+%s" % [pair[0], pair[1]]
	)
	var table: Dictionary = RouterDiff.read(path)
	if table.is_empty():
		_fail("no reachability table at %s. Write it: %s" % [path, command])
		return
	var stale: String = RouterDiff.staleness(table, graph, tables.lane_width_m)
	if not stale.is_empty():
		_fail("%s is stale: %s. Re-run: %s" % [path, stale, command])
		return
	var populations: Dictionary = table.get("populations", {})
	for label: String in ["control", "lane"]:
		var bar: RoadRouter.Profile.Bar = (
			RoadRouter.Profile.Bar.NONE if label == "control" else RoadRouter.Profile.Bar.LANE
		)
		var router: RoadRouter = RouterScript.new(graph, RoadRouter.Profile.survey(bar))
		for problem: String in RouterDiff.check_population(
			router, populations.get(label, {}), ROUTE_TOLERANCE_M, label
		):
			_fail(problem)


func _dump(dir: String, merged: Dictionary, tables: Manifest, clearance: Dictionary) -> void:
	if DirAccess.make_dir_recursive_absolute(dir) != OK:
		_fail("could not create %s" % dir)
		return
	var rows: Array = []
	var ids: Array = tables.carriageway_clear_width_m.keys()
	ids.sort()
	for edge: int in ids:
		rows.append({"edge": edge, "clear_width_m": Array(tables.carriageway_clear_width_m[edge])})
	var out: Dictionary = clearance.duplicate()
	out["region_id"] = merged.get("region_id")
	out["clearance"] = rows
	for pair: Array in [["roadgraph.json", merged], ["clearance.json", out]]:
		var file := FileAccess.open(dir.path_join(pair[0]), FileAccess.WRITE)
		if file == null:
			_fail("could not write %s" % dir.path_join(pair[0]))
			return
		file.store_string(JSON.stringify(pair[1]))
	print("  dump  %s" % dir)


static func _gap(a: Variant, b: Variant) -> float:
	var pa: Array = a as Array
	var pb: Array = b as Array
	return maxf(
		absf(float(pa[0]) - float(pb[0])),
		maxf(absf(float(pa[1]) - float(pb[1])), absf(float(pa[2]) - float(pb[2])))
	)


static func _read(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	return parsed if parsed is Dictionary else {}


func _fail(message: String) -> void:
	_problems.append(message)


func _finish(pair: PackedStringArray) -> void:
	for problem: String in _problems:
		printerr("  FAIL  ", problem)
	print(
		(
			"%s + %s: runtime merge against pipeline/join.py, %d problem(s)"
			% [pair[0], pair[1], _problems.size()]
		)
	)
	quit(1 if not _problems.is_empty() else 0)
