## Diffs a `RoadRouter` against `tools/reachability.py --json` (`P3-43`).
##
## Shared by `verify_road_graph.gd` (one region) and `verify_join.gd` (the
## merge), so the two cannot drift in what "agrees" means. The tool's table is
## by source row; the router answers by destination column (`distances_to`,
## which is its shipped search run once per goal); every cell is in exactly one
## of each, so walking the columns and looking each cell up in the rows diffs
## the whole table — and counts the cells only one side has.
##
## 🔴 **The admitted set is compared as a set first.** The `lane` population's
## edges are `starved`'s complement in Python and `is_passable`'s here; a router
## that routed the same pairs over a different network would be agreeing by
## accident, and the edge list is what says it is the same network.
extends RefCounted

const RouterScript = preload("res://scripts/city/road_router.gd")

## How many offending pairs to name before counting the rest.
const NAMED: int = 5


## The parsed table, or `{}` for a missing or unreadable file.
static func read(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	return parsed if parsed is Dictionary else {}


## What writes the file `read` could not find.
static func reference_command(region: String, graph_dir: String) -> String:
	var command: String = ".venv/bin/python tools/reachability.py --region %s" % region
	if not graph_dir.is_empty():
		command += " --graph-dir %s" % graph_dir
	return command + " --json"


## "" where the table was routed over this graph, else what disagrees.
##
## The file is a grader's reading of a bundle that has since been rebuilt if
## these move, and diffing a router against a stale table would fail on the
## bundle rather than on the router.
static func staleness(table: Dictionary, graph: RoadGraph, lane_width_m: float) -> String:
	var edges: int = int(table.get("edges", -1))
	var turns: int = int(table.get("turn_restrictions", -1))
	var bar: float = float(table.get("lane_width_m", -1.0))
	if edges != graph.edge_count():
		return "routed over %d edges, this graph has %d" % [edges, graph.edge_count()]
	if turns != graph.turn_restriction_count():
		return (
			"routed with %d turn restrictions, this graph has %d"
			% [turns, graph.turn_restriction_count()]
		)
	if absf(bar - lane_width_m) > 1e-6:
		return "routed at a %.3f m lane bar, this manifest's is %.3f m" % [bar, lane_width_m]
	return ""


## Every pair of one population, routed here and compared: the admitted edges
## as a set, then each cell within `tolerance_m`, and the cells either side
## lacks. `label` names the population in the problems and the summary line.
static func check_population(
	router: RoadRouter, population: Dictionary, tolerance_m: float, label: String
) -> PackedStringArray:
	var problems: PackedStringArray = []

	var theirs: Dictionary[int, bool] = {}
	for edge: Variant in population.get("edges", []):
		theirs[int(edge)] = true
	var ours: Dictionary[int, bool] = {}
	for edge_id: int in router.admitted_edge_ids():
		ours[edge_id] = true
	var only_theirs: PackedInt32Array = []
	for edge_id: int in theirs:
		if not ours.has(edge_id):
			only_theirs.append(edge_id)
	var only_ours: PackedInt32Array = []
	for edge_id: int in ours:
		if not theirs.has(edge_id):
			only_ours.append(edge_id)
	if not only_theirs.is_empty() or not only_ours.is_empty():
		(
			problems
			. append(
				(
					"%s: the router admits %d edges, the tool %d — %d only the tool's (%s), %d only ours (%s)"
					% [
						label,
						ours.size(),
						theirs.size(),
						only_theirs.size(),
						_named(only_theirs),
						only_ours.size(),
						_named(only_ours),
					]
				)
			)
		)

	# The tool's rows, re-keyed for the lookup: source -> target -> metres.
	var rows: Dictionary[int, Dictionary] = {}
	var their_pairs: int = 0
	var distances: Dictionary = population.get("distances", {})
	for source: String in distances:
		var row: Dictionary = distances[source]
		var targets: Array = row.get("to", [])
		var metres: Array = row.get("m", [])
		var cells: Dictionary = {}
		for index: int in targets.size():
			cells[int(targets[index])] = float(metres[index])
		rows[int(source)] = cells
		their_pairs += cells.size()

	var matched: int = 0
	var extra: int = 0
	var mismatched: int = 0
	var worst_m: float = 0.0
	var worst_pair: String = ""
	var named: PackedStringArray = []
	for target: int in router.admitted_edge_ids():
		var column: Dictionary = router.distances_to(target)
		for source: Variant in column:
			var source_id: int = int(source)
			var ours_m: float = float(column[source])
			if not rows.has(source_id) or not rows[source_id].has(target):
				extra += 1
				if named.size() < NAMED:
					named.append(
						"e%d -> e%d routed here only (%.3f m)" % [source_id, target, ours_m]
					)
				continue
			matched += 1
			var delta_m: float = absf(ours_m - float(rows[source_id][target]))
			if delta_m > worst_m:
				worst_m = delta_m
				worst_pair = "e%d -> e%d" % [source_id, target]
			if delta_m > tolerance_m:
				mismatched += 1
				if named.size() < NAMED:
					named.append(
						(
							"e%d -> e%d: %.6f m here, %.6f m in the tool"
							% [source_id, target, ours_m, float(rows[source_id][target])]
						)
					)
	var missing: int = their_pairs - matched
	if missing > 0 or extra > 0 or mismatched > 0:
		problems.append(
			(
				"%s: %d pairs matched, %d only the tool's, %d only ours, %d over %.3f m"
				% [label, matched, missing, extra, mismatched, tolerance_m]
			)
		)
		for line: String in named:
			problems.append("%s: %s" % [label, line])
	if their_pairs == 0:
		problems.append("%s: the tool's table is empty; nothing was diffed" % label)
	print(
		(
			"  router[%s]: %d edges, %d states, %d pairs diffed, worst %.6f m at %s"
			% [label, ours.size(), router.state_count(), matched, worst_m, worst_pair]
		)
	)
	return problems


static func _named(ids: PackedInt32Array) -> String:
	var parts: PackedStringArray = []
	for index: int in mini(ids.size(), NAMED):
		parts.append("e%d" % ids[index])
	if ids.size() > NAMED:
		parts.append("...")
	return ", ".join(parts) if not parts.is_empty() else "-"
