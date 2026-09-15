## Two regions' road graphs as one, in the first region's frame (`P5-9d`).
##
## A rule-for-rule mirror of `etl/pipeline/join.py`, which is the reference:
## `verify_join.gd` diffs this against the Python merge field by field, so a rule
## changed on one side only fails there. The rules, in `join.py`'s order:
##
## * each region publishes the runs it owns under `edges` and the neighbour's runs
##   that reach into it under `foreign_edges` (`P5-7e`); the owner's copy is kept
##   and the foreign one dropped;
## * a run both regions own is refused, because a merge cannot pick;
## * the seam nodes are named by **identity** — a foreign copy's `from` and `to`
##   are the owner's ends — keyed on `(source_id, run)`, never by a distance;
## * the frame's ids are kept and the second region's edges renumbered from the
##   frame's `max + 1`, gaps and all; its other nodes are appended in order;
## * the second region's positions move by `delta`, at millimetre precision;
## * `kind` is recomputed, because a seam node has arms from both regions now;
## * turns are remapped through the renumbering, the foreign-arm alias and the
##   node map, and a turn naming an arm neither map knows is dropped and counted.
##
## 🔴 **The id maps are the point, not a by-product.** `clearance`, `city.json`'s
## `carriageway[]`, `fence.json` and `fares.json` all key on per-region integer
## ids that start at 0 in every region, and `join.py` remaps only the first — the
## rest are not the ETL's to merge. So `edge_of` answers, per region, the merged
## id of every edge id that region's documents may name: an owned edge's
## renumbering, and a foreign copy's alias of its owner. No document is edited.
extends RefCounted

const JUNCTION: String = "junction"
const ENDPOINT: String = "endpoint"


## The merge of `a` and `b`, or `{"error": message}`. On success:
## `graph` — the merged document, `roadgraph.json`'s shape with `foreign_edges`
## empty; `edge_of` — two `Dictionary[int, int]`, `a`'s ids and `b`'s ids to
## merged ids; `node_of_b` — `b`'s node ids to merged ones; `report` — `join.json`'s
## counters.
static func merge(
	a: Dictionary, b: Dictionary, delta: Vector3, regions: PackedStringArray
) -> Dictionary:
	var a_owned: Dictionary = _by_identity(a.get("edges", []))
	var b_owned: Dictionary = _by_identity(b.get("edges", []))
	var a_foreign: Dictionary = _by_identity(a.get("foreign_edges", []))
	var b_foreign: Dictionary = _by_identity(b.get("foreign_edges", []))
	for key: Vector2i in a_owned:
		if b_owned.has(key):
			return {"error": "run %s is owned by both %s and %s" % [key, regions[0], regions[1]]}
	var report: Dictionary = {
		"frame": regions[0],
		"regions": [regions[0], regions[1]],
		"owned_a": a_owned.size(),
		"owned_b": b_owned.size(),
		"foreign_matched": 0,
		"foreign_unmatched": 0,
		"nodes": 0,
		"nodes_unified": 0,
		"edges": 0,
		"turns": 0,
		"turns_dropped": 0,
	}

	var node_of_b: Dictionary[int, int] = {}
	var edge_of_a: Dictionary[int, int] = {}
	var edge_of_b: Dictionary[int, int] = {}
	var alias_a: Dictionary[int, int] = {}
	var alias_b: Dictionary[int, int] = {}
	var next_id: int = 0
	for edge: Dictionary in a.get("edges", []):
		var id: int = int(edge["id"])
		edge_of_a[id] = id
		next_id = maxi(next_id, id + 1)
	for edge: Dictionary in b.get("edges", []):
		edge_of_b[int(edge["id"])] = next_id
		next_id += 1

	for key: Vector2i in a_foreign:
		var copy: Dictionary = a_foreign[key]
		if not b_owned.has(key):
			report["foreign_unmatched"] += 1
			continue
		var owner: Dictionary = b_owned[key]
		report["foreign_matched"] += 1
		var clash: String = _unify(node_of_b, int(owner["from"]), int(copy["from"]), regions)
		clash += _unify(node_of_b, int(owner["to"]), int(copy["to"]), regions)
		if not clash.is_empty():
			return {"error": clash}
		alias_a[int(copy["id"])] = edge_of_b[int(owner["id"])]
	for key: Vector2i in b_foreign:
		var copy: Dictionary = b_foreign[key]
		if not a_owned.has(key):
			report["foreign_unmatched"] += 1
			continue
		var owner: Dictionary = a_owned[key]
		report["foreign_matched"] += 1
		var clash: String = _unify(node_of_b, int(copy["from"]), int(owner["from"]), regions)
		clash += _unify(node_of_b, int(copy["to"]), int(owner["to"]), regions)
		if not clash.is_empty():
			return {"error": clash}
		alias_b[int(copy["id"])] = int(owner["id"])
	report["nodes_unified"] = node_of_b.size()

	var nodes: Array = []
	for node: Dictionary in a.get("nodes", []):
		nodes.append(node.duplicate())
	for node: Dictionary in b.get("nodes", []):
		var b_id: int = int(node["id"])
		if node_of_b.has(b_id):
			continue
		node_of_b[b_id] = nodes.size()
		nodes.append({"id": nodes.size(), "pos": moved(node["pos"], delta), "kind": node["kind"]})

	var edges: Array = []
	for edge: Dictionary in a.get("edges", []):
		edges.append(edge.duplicate())
	for edge: Dictionary in b.get("edges", []):
		var shifted: Dictionary = edge.duplicate()
		shifted["id"] = edge_of_b[int(edge["id"])]
		shifted["from"] = node_of_b[int(edge["from"])]
		shifted["to"] = node_of_b[int(edge["to"])]
		var polyline: Array = []
		for point: Variant in edge.get("polyline", []):
			polyline.append(moved(point, delta))
		shifted["polyline"] = polyline
		edges.append(shifted)
	_rekind(nodes, edges)

	var no_nodes: Dictionary[int, int] = {}
	var turns: Array = _remap_turns(
		a.get("turn_restrictions", []), edge_of_a, alias_a, no_nodes, report
	)
	turns.append_array(
		_remap_turns(b.get("turn_restrictions", []), edge_of_b, alias_b, node_of_b, report)
	)

	var graph: Dictionary = {
		"schema_version": a.get("schema_version"),
		"city_id": a.get("city_id"),
		"region_id": "+".join(regions),
		"frame": regions[0],
		"nodes": nodes,
		"edges": edges,
		"foreign_edges": [],
		"turn_restrictions": turns,
	}
	report["nodes"] = nodes.size()
	report["edges"] = edges.size()
	report["turns"] = turns.size()

	# Every id a region's documents may name: its owned edges, and its foreign
	# copies through the alias. A foreign copy with no owner has no merged id.
	for foreign: int in alias_a:
		edge_of_a[foreign] = alias_a[foreign]
	for foreign: int in alias_b:
		edge_of_b[foreign] = alias_b[foreign]
	return {
		"graph": graph, "edge_of": [edge_of_a, edge_of_b], "node_of_b": node_of_b, "report": report
	}


## A position moved by `delta`, at millimetre precision — `round_position`.
static func moved(point: Variant, delta: Vector3) -> Array:
	var values: Array = point as Array
	return [
		snappedf(float(values[0]) + delta.x, 0.001) + 0.0,
		snappedf(float(values[1]) + delta.y, 0.001) + 0.0,
		snappedf(float(values[2]) + delta.z, 0.001) + 0.0,
	]


static func _by_identity(edges: Array) -> Dictionary:
	var found: Dictionary = {}
	for edge: Dictionary in edges:
		found[Vector2i(int(edge["source_id"]), int(edge["run"]))] = edge
	return found


## Names `b_node` as `a_node`, or the message when it is already named otherwise.
static func _unify(
	node_of_b: Dictionary[int, int], b_node: int, a_node: int, regions: PackedStringArray
) -> String:
	if node_of_b.has(b_node) and node_of_b[b_node] != a_node:
		return (
			"node %d of %s is named as two nodes of %s: %d and %d"
			% [b_node, regions[1], regions[0], node_of_b[b_node], a_node]
		)
	node_of_b[b_node] = a_node
	return ""


static func _remap_turns(
	turns: Array,
	renumbered: Dictionary[int, int],
	alias: Dictionary[int, int],
	node_of: Dictionary[int, int],
	report: Dictionary
) -> Array:
	var kept: Array = []
	for turn: Dictionary in turns:
		var arms: Array[int] = []
		for key: String in ["from_edge", "to_edge"]:
			var id: int = int(turn[key])
			if renumbered.has(id):
				arms.append(renumbered[id])
			elif alias.has(id):
				arms.append(alias[id])
		if arms.size() < 2:
			report["turns_dropped"] += 1
			continue
		var via: int = int(turn["via_node"])
		kept.append({"from_edge": arms[0], "via_node": node_of.get(via, via), "to_edge": arms[1]})
	return kept


static func _rekind(nodes: Array, edges: Array) -> void:
	var degree: PackedInt32Array = PackedInt32Array()
	degree.resize(nodes.size())
	for edge: Dictionary in edges:
		degree[int(edge["from"])] += 1
		degree[int(edge["to"])] += 1
	for node: Dictionary in nodes:
		node["kind"] = JUNCTION if degree[int(node["id"])] >= 3 else ENDPOINT
