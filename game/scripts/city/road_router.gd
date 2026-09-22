class_name RoadRouter
extends RefCounted
## Routes over `RoadGraph`: one-way, the turn restrictions, and a bar (`P3-43`).
##
## The graph is a spatial index and an attribute table; this is the traversal
## over it, built from its accessors and never inside it. `P3-1a` asks it for a
## fare's road distance — in a region 93.5% one-way by drivable length, two
## stands 200 m apart can be a far longer drive — and `P3-3` for a route traffic
## may legally take.
##
## 🔴 **The search state is a DIRECTED EDGE, not a node.** A turn restriction is
## `from_edge -> via_node -> to_edge`, which a node search cannot express: "no
## right from HENNESSY into CANAL" bans one movement through a junction that
## both roads pass through. One state per one-way edge, two per two-way edge,
## and a two-way street is genuinely two positions to be in — only one of them
## can reach what lies beyond its far end.
##
## 🔴 **One search per DESTINATION, not per query.** `prepare` runs a reverse
## Dijkstra from the goal once and keeps the tree; `route` from anywhere is then
## a lookup and a path walk. The per-query search was measured and refused:
## 40% of ordered fare pairs in Wan Chai have no route (the clip is not strongly
## connected — `reachability.py`'s largest component is 331 of 734 edges), and
## an unreachable query exhausts its component whatever the heuristic, 463–641
## states, which GDScript settles at 3–5 ms. Prepared, a route reads in tens
## of microseconds, which is the 1 ms the plan budgets. Call `prepare` at the
## hail and `route` off the `Hit` `hud.gd` already fetches at 5 Hz, or on
## leaving the path. Never per frame.
##
## 🔴 **`tools/reachability.py` is the second implementation, and the truth this
## is diffed against** — `verify_road_graph.gd` and `verify_join.gd` route every
## pair its `--json` publishes and compare at a millimetre. Its cost convention
## is kept exactly: entering an edge costs that edge's whole plan length, the
## source's own length is excluded and the target's included. Here that is
## reversed — `to_goal[state]` is the metres from a state's ENTRY node, driving
## it fully, to the goal — so a table cell is the least `to_goal` over the
## source's successors. Neither side imports the other (`Q95`'s arrangement).
##
## ⚠️ **"No route" is an answer, never an assert.** `Route.found` is false, the
## edge list is empty and `distance_m` is the straight-line plan distance, the
## same fallback `PLAN.md` names. A fare between two clipped components is a
## fact about the region, not a fault in the caller.


## Which rules a search obeys, and which bar it reads (`Q19`: two bars, one
## measurement, never merged — each is read by its own predicate here).
class Profile:
	extends RefCounted

	## `NONE` admits every drivable edge; `LANE` reads `is_passable` (3.20 m, what
	## traffic is routed on); `CAR` reads `fits_car` (1.80 m, what the player is
	## fenced at).
	enum Bar { NONE, LANE, CAR }

	## Drive a one-way edge its signed way only.
	var obey_direction: bool = true
	## Refuse the published turn restrictions.
	var obey_turns: bool = true
	## Allow leaving an edge onto the same edge the other way. The source never
	## publishes a U-turn, and `reachability.py` bans it; the player may make one.
	var allow_u_turn: bool = false
	var bar: Bar = Bar.LANE
	## Level-0 edges only, `reachability.py`'s population; `is_drivable` otherwise.
	var at_grade_only: bool = false

	## Traffic: every rule, the lane bar. `admits` is `RoadGraph.is_routable`.
	static func legal() -> Profile:
		return Profile.new()

	## The player: "may break every traffic rule", the car bar. `admits` is
	## `is_drivable and fits_car` — exactly where the fence lets them go.
	static func player() -> Profile:
		var profile := Profile.new()
		profile.obey_direction = false
		profile.obey_turns = false
		profile.allow_u_turn = true
		profile.bar = Bar.CAR
		return profile

	## `reachability.py`'s own population: level 0, every rule, no U-turn.
	## `NONE` is its `nothing (control)` row and `LANE` its `starved at one lane`.
	static func survey(at_bar: Bar) -> Profile:
		var profile := Profile.new()
		profile.at_grade_only = true
		profile.bar = at_bar
		return profile

	## Whether an edge is in this profile's network at all.
	func admits(graph: RoadGraph, edge_id: int) -> bool:
		if at_grade_only:
			if graph.level_of(edge_id) != 0:
				return false
		elif not graph.is_drivable(edge_id):
			return false
		match bar:
			Bar.LANE:
				return graph.is_passable(edge_id)
			Bar.CAR:
				return graph.fits_car(edge_id)
		return true


## A route between two points on the network, or the defined answer for none.
class Route:
	extends RefCounted

	## Edge ids from the source edge to the destination edge inclusive; empty
	## when `found` is false.
	var edges: PackedInt32Array = PackedInt32Array()
	## 1 where the edge is driven along its own vertex order, 0 against it —
	## parallel to `edges`. Against on a one-way edge is what "wrong way" means.
	var forward: PackedByteArray = PackedByteArray()
	## Metres driven, from the source point to the destination point; the plan
	## distance when `found` is false.
	var distance_m: float = 0.0
	## Straight-line plan distance between the two points, always filled.
	var plan_m: float = 0.0
	var found: bool = false


## The reverse search from one destination point: what every state costs to the
## goal, and which state it leaves through.
class GoalTree:
	extends RefCounted

	var edge_id: int = -1
	var t: float = 0.0
	var to_goal: PackedFloat64Array = PackedFloat64Array()
	## The state after each state on its route to the goal; -1 at the goal.
	var next: PackedInt32Array = PackedInt32Array()


## How many destinations' trees are kept. A fare has one; the cap only bounds a
## caller that prepares many.
const TREE_CACHE: int = 8

var _graph: RoadGraph = null
var _profile: Profile = null

# One entry per state. A state is an edge driven one way: `_state_forward` is 1
# along the vertex order (entry `from`, exit `to`) and 0 against it.
var _state_edge: PackedInt32Array = PackedInt32Array()
var _state_forward: PackedByteArray = PackedByteArray()
var _state_exit: PackedInt32Array = PackedInt32Array()
var _length: PackedFloat64Array = PackedFloat64Array()
var _states_of: Dictionary[int, PackedInt32Array] = {}
# Every admitted edge id, in document order, deduplicated.
var _admitted: PackedInt32Array = PackedInt32Array()

# Successors and predecessors in CSR form: the arcs out of state `s` are
# `_succ[_succ_start[s] .. _succ_start[s + 1])`, and likewise `_pred`.
var _succ_start: PackedInt32Array = PackedInt32Array()
var _succ: PackedInt32Array = PackedInt32Array()
var _pred_start: PackedInt32Array = PackedInt32Array()
var _pred: PackedInt32Array = PackedInt32Array()

# The search's binary heap, preallocated once to the most pushes a search can
# make (one per relaxation, and a relaxation is an arc) so a search allocates
# nothing. Lazy deletion: a popped entry stale against `to_goal` is skipped.
var _heap_cost: PackedFloat64Array = PackedFloat64Array()
var _heap_state: PackedInt32Array = PackedInt32Array()
var _heap_size: int = 0

# Prepared destinations by edge id, in insertion order for eviction.
var _trees: Dictionary[int, GoalTree] = {}


func _init(graph: RoadGraph, rules: Profile) -> void:
	_graph = graph
	_profile = rules
	_build()


## The profile this router was built with.
func profile() -> Profile:
	return _profile


func state_count() -> int:
	return _state_edge.size()


## Every edge in this profile's network, in document order.
func admitted_edge_ids() -> PackedInt32Array:
	return _admitted.duplicate()


func is_admitted(edge_id: int) -> bool:
	return _states_of.has(edge_id)


## Search from a destination point once, so that `route` to it is a lookup.
##
## False when the edge is not in this profile's network. A prepared tree is
## kept until `TREE_CACHE` more are prepared, and rebuilt if `t` moves.
func prepare(edge_id: int, t: float) -> bool:
	if not _states_of.has(edge_id):
		return false
	if _trees.has(edge_id) and _trees[edge_id].t == t:
		return true
	if not _trees.has(edge_id) and _trees.size() >= TREE_CACHE:
		_trees.erase(_trees.keys()[0])
	var clamped: float = clampf(t, 0.0, 1.0)
	var length_m: float = _graph.plan_length_of(edge_id)
	var tree: GoalTree = _search(edge_id, clamped * length_m, (1.0 - clamped) * length_m)
	tree.t = t
	_trees[edge_id] = tree
	return true


## The shortest drive from `from_t` along `from_edge` to `to_t` along `to_edge`.
##
## Prepares the destination if it has not been. Either point off the network
## gives the defined answer rather than a route: `found` false, plan distance.
func route(from_edge: int, from_t: float, to_edge: int, to_t: float) -> Route:
	var result := Route.new()
	result.plan_m = RoadGraph.plan_distance(
		_graph.point_at(from_edge, from_t), _graph.point_at(to_edge, to_t)
	)
	result.distance_m = result.plan_m
	if not _states_of.has(from_edge) or not prepare(to_edge, to_t):
		return result
	var tree: GoalTree = _trees[to_edge]
	var source_t: float = clampf(from_t, 0.0, 1.0)
	var target_t: float = clampf(to_t, 0.0, 1.0)
	var length_m: float = _graph.plan_length_of(from_edge)

	var best: float = INF
	var best_state: int = -1
	var best_onward: int = -1
	for state: int in _states_of[from_edge]:
		var along: bool = _state_forward[state] == 1
		# Staying on the edge, where the destination lies ahead in this
		# direction of travel. A loop back round to a point behind falls out of
		# the junction search below, since the goal seeds its own edge's states.
		if from_edge == to_edge:
			var direct: float = (target_t - source_t) if along else (source_t - target_t)
			if direct >= 0.0 and direct * length_m < best:
				best = direct * length_m
				best_state = state
				best_onward = -1
		var partial: float = ((1.0 - source_t) if along else source_t) * length_m
		for arc: int in range(_succ_start[state], _succ_start[state + 1]):
			var onward: int = _succ[arc]
			var candidate: float = partial + tree.to_goal[onward]
			if candidate < best:
				best = candidate
				best_state = state
				best_onward = onward
	if best_state < 0:
		return result

	result.found = true
	result.distance_m = best
	result.edges.append(from_edge)
	result.forward.append(_state_forward[best_state])
	var state: int = best_onward
	while state >= 0:
		result.edges.append(_state_edge[state])
		result.forward.append(_state_forward[state])
		state = tree.next[state]
	return result


## `reachability.py`'s table, one column: the distance from every other edge in
## the network to `edge_id`, in its convention — the source's own length
## excluded, the target's whole length included, the least over a two-way
## edge's two directions. Edges with no route are absent.
##
## Searched fresh and not cached, on the shipped path (`_pred`, the heap, the
## tree) rather than a second forward search written for the check: a divergence
## from the tool is then a divergence in what ships.
func distances_to(edge_id: int) -> Dictionary:
	var column: Dictionary = {}
	if not _states_of.has(edge_id):
		return column
	var length_m: float = _graph.plan_length_of(edge_id)
	var tree: GoalTree = _search(edge_id, length_m, length_m)
	for source: int in _admitted:
		if source == edge_id:
			continue
		var best: float = INF
		for state: int in _states_of[source]:
			for arc: int in range(_succ_start[state], _succ_start[state + 1]):
				best = minf(best, tree.to_goal[_succ[arc]])
		if best < INF:
			column[source] = best
	return column


func _build() -> void:
	var seen: Dictionary[int, bool] = {}
	# States entering at each node, for the arcs: a transition is a lookup at
	# the exit node rather than a scan of every state per junction.
	var leaving: Dictionary[int, PackedInt32Array] = {}
	for edge_id: int in _graph.edge_ids():
		# `_by_id` is not injective; the graph's accessors answer for the last
		# of two edges sharing an id, so the second sighting would repeat it.
		if seen.has(edge_id):
			continue
		seen[edge_id] = true
		if not _profile.admits(_graph, edge_id):
			continue
		var from_node: int = _graph.from_node_of(edge_id)
		var to_node: int = _graph.to_node_of(edge_id)
		if from_node < 0 or to_node < 0:
			continue
		_admitted.append(edge_id)
		var length_m: float = _graph.plan_length_of(edge_id)
		var states := PackedInt32Array()
		states.append(_add_state(edge_id, 1, from_node, to_node, length_m, leaving))
		if not _graph.is_one_way(edge_id) or not _profile.obey_direction:
			states.append(_add_state(edge_id, 0, to_node, from_node, length_m, leaving))
		_states_of[edge_id] = states

	var count: int = _state_edge.size()
	_succ_start.resize(count + 1)
	_succ_start.fill(0)
	var arcs := PackedInt32Array()
	for state: int in count:
		_succ_start[state] = arcs.size()
		var edge_id: int = _state_edge[state]
		var exit_node: int = _state_exit[state]
		for onward: int in leaving.get(exit_node, PackedInt32Array()):
			if onward == state:
				continue
			# Onto the same edge the other way. Not a movement the source
			# publishes; allowing it would let a car turn round on a blocked
			# edge's own carriageway and restore a route the wall removed.
			if _state_edge[onward] == edge_id and not _profile.allow_u_turn:
				continue
			if (
				_profile.obey_turns
				and _graph.is_turn_banned(edge_id, exit_node, _state_edge[onward])
			):
				continue
			arcs.append(onward)
	_succ_start[count] = arcs.size()
	_succ = arcs

	# The transpose, for the reverse search: who can enter each state.
	var degree := PackedInt32Array()
	degree.resize(count)
	degree.fill(0)
	for onward: int in _succ:
		degree[onward] += 1
	_pred_start.resize(count + 1)
	_pred_start[0] = 0
	for state: int in count:
		_pred_start[state + 1] = _pred_start[state] + degree[state]
	_pred.resize(arcs.size())
	var cursor: PackedInt32Array = _pred_start.duplicate()
	for state: int in count:
		for arc: int in range(_succ_start[state], _succ_start[state + 1]):
			var onward: int = _succ[arc]
			_pred[cursor[onward]] = state
			cursor[onward] += 1

	_heap_cost.resize(arcs.size() + count + 2)
	_heap_state.resize(arcs.size() + count + 2)


func _add_state(
	edge_id: int,
	along: int,
	entry: int,
	exit_node: int,
	length_m: float,
	leaving: Dictionary[int, PackedInt32Array]
) -> int:
	var state: int = _state_edge.size()
	_state_edge.append(edge_id)
	_state_forward.append(along)
	_state_exit.append(exit_node)
	_length.append(length_m)
	if not leaving.has(entry):
		leaving[entry] = PackedInt32Array()
	leaving[entry].append(state)
	return state


## Reverse Dijkstra from the goal edge's states, seeded with what each costs to
## drive from its entry to the goal point: `seed_forward` along the vertex
## order, `seed_backward` against it.
func _search(edge_id: int, seed_forward: float, seed_backward: float) -> GoalTree:
	var tree := GoalTree.new()
	tree.edge_id = edge_id
	var count: int = _state_edge.size()
	tree.to_goal.resize(count)
	tree.to_goal.fill(INF)
	tree.next.resize(count)
	tree.next.fill(-1)
	_heap_size = 0
	for state: int in _states_of[edge_id]:
		var seed: float = seed_forward if _state_forward[state] == 1 else seed_backward
		tree.to_goal[state] = seed
		_push(seed, state)
	while _heap_size > 0:
		var cost: float = _heap_cost[0]
		var state: int = _heap_state[0]
		_pop()
		if cost > tree.to_goal[state]:
			continue
		for arc: int in range(_pred_start[state], _pred_start[state + 1]):
			var before: int = _pred[arc]
			# Entering `before` costs its whole edge, then whatever `state`
			# already costs from its own entry — reachability's convention, run
			# backwards.
			var candidate: float = _length[before] + cost
			if candidate < tree.to_goal[before]:
				tree.to_goal[before] = candidate
				tree.next[before] = state
				_push(candidate, before)
	return tree


func _push(cost: float, state: int) -> void:
	var index: int = _heap_size
	_heap_size += 1
	while index > 0:
		var parent: int = (index - 1) >> 1
		if _heap_cost[parent] <= cost:
			break
		_heap_cost[index] = _heap_cost[parent]
		_heap_state[index] = _heap_state[parent]
		index = parent
	_heap_cost[index] = cost
	_heap_state[index] = state


func _pop() -> void:
	_heap_size -= 1
	if _heap_size == 0:
		return
	var cost: float = _heap_cost[_heap_size]
	var state: int = _heap_state[_heap_size]
	var index: int = 0
	while true:
		var child: int = index * 2 + 1
		if child >= _heap_size:
			break
		if child + 1 < _heap_size and _heap_cost[child + 1] < _heap_cost[child]:
			child += 1
		if _heap_cost[child] >= cost:
			break
		_heap_cost[index] = _heap_cost[child]
		_heap_state[index] = _heap_state[child]
		index = child
	_heap_cost[index] = cost
	_heap_state[index] = state
