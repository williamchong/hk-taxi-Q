class_name SignalHeads
extends Node3D
## The published signal heads, lit by their controller (`P3-3e`, `Q173`).
##
## Each region's `signal_heads_placements.json` stands the AUTHORED
## `assets/authored/signals/heads.glb` at every post the ETL bound to an
## approach (`etl/pipeline/signals.py`'s `bind_heads`). A child of the
## `SignalController` it shows, so no controller means no heads.
##
## 🔴 **Never a dark head** (`Q77`): a placement whose approach the plan does
## not hold, or holds at another junction or stage, is a `push_error` and is
## not drawn — a lamp showing nothing would read as a junction that is off.
## The light is `SignalController.light_at` for the head's own approach, the one
## the cars stop by, written into `INSTANCE_CUSTOM.a` only when it changes
## (`signal_head.gdshader` decodes it). With `posts`, the post each head
## stands on collides: a cylinder read off the library mesh's foot, a body a
## plan cell (`PropBatch.posts`, `Q191`). The head itself stays collider-free.

const GeneratedPlacements = preload("res://scripts/city/generated_placements.gd")
const GeneratedRegions = preload("res://scripts/city/generated_regions.gd")
const PropBatch = preload("res://scripts/city/prop_batch.gd")

## The library's one mesh: `SIGNAL_HEAD_MESH` in `etl/pipeline/signals.py`.
const MESH_NAME: String = "head"


## One head: the approach it shows and where its datum is written.
class Head:
	extends RefCounted

	var junction: SignalPlan.Junction
	var approach: SignalPlan.Approach
	var at: Transform3D
	var multimesh: MultiMesh
	var slot: int
	## The light last written; -1 before the first.
	var light: int = -1


## The heads showing one stage of one junction. `light_at` reads only the
## junction, the stage and the clock, so they show one light, asked once a tick.
class Stage:
	extends RefCounted

	var junction: SignalPlan.Junction
	## Any one of the stage's approaches: `light_at` reads only its `stage`.
	var approach: SignalPlan.Approach
	var light: int = -1
	var heads: Array[Head] = []


## Stand a cylinder up every head's post. On in `city_drive.tscn`; the
## sidecar says why, and `false` is the off switch.
@export var posts: bool = false

var heads: Array[Head] = []
var _stages: Array[Stage] = []
## Placements refused because the plan does not hold their approach, by region.
var unresolved: Dictionary[String, int] = {}
var controller: SignalController


func _ready() -> void:
	controller = get_parent() as SignalController
	if controller == null:
		push_error("SignalHeads: not a child of a SignalController; no heads drawn")
		set_physics_process(false)
		return
	# A child is ready before its parent, and the controller loads its plan in
	# its own `_ready`.
	if not controller.is_node_ready():
		await controller.ready
	build(RoadGraph.shared())


## Stand every resident region's heads against the controller's plan.
func build(graph: RoadGraph) -> void:
	if controller.plan == null or controller.plan.is_empty():
		set_physics_process(false)
		return
	var cells := load(PropCellProfile.PATH) as PropCellProfile
	if cells == null or cells.cell_m <= 0.0:
		push_error("SignalHeads: %s is not usable; no heads drawn" % PropCellProfile.PATH)
		set_physics_process(false)
		return
	var mesh: Mesh = null
	var by_cell: Dictionary[Vector2i, Array] = {}
	for region: String in GeneratedRegions.resident():
		var manifest: CityManifest = CityManifest.shared(region)
		if manifest == null or manifest.signal_heads_placements_path.is_empty():
			continue
		var document: Dictionary = GeneratedPlacements.load_placements(
			manifest.signal_heads_placements_path, "signal heads"
		)
		if document.is_empty():
			continue
		if mesh == null:
			mesh = _library_mesh(String(document.get("library", "")))
			if mesh == null:
				set_physics_process(false)
				return
		var offset: Vector3 = graph.region_offset(region)
		for raw: Dictionary in document.get("placements", []) as Array:
			var head: Head = _resolve(raw, region, graph)
			var placed: Variant = GeneratedPlacements.placement_of(raw)
			if head == null or placed == null:
				unresolved[region] = unresolved.get(region, 0) + 1
				continue
			head.at = (placed as Transform3D).translated(offset)
			var cell: Vector2i = cells.cell_of(head.at.origin)
			if not by_cell.has(cell):
				by_cell[cell] = []
			by_cell[cell].append(head)
		if unresolved.get(region, 0) > 0:
			push_error(
				(
					"SignalHeads: %d of %s's heads show no approach the plan holds; not drawn"
					% [unresolved[region], region]
				)
			)
	var by_stage: Dictionary[String, Stage] = {}
	for cell: Vector2i in by_cell:
		var batch: Array[Head] = []
		batch.assign(by_cell[cell])
		var transforms: Array[Transform3D] = []
		# `INSTANCE_CUSTOM` on, all dark until the first `refresh`.
		var dark := PackedColorArray()
		for head: Head in batch:
			transforms.append(head.at)
			dark.append(Color(0.0, 0.0, 0.0, 0.0))
		var node: MultiMeshInstance3D = PropBatch.batch(
			mesh, transforms, "%s_%d_%d" % [MESH_NAME, cell.x, cell.y], dark
		)
		node.visibility_range_end = cells.range_m
		node.visibility_range_end_margin = cells.range_margin_m
		add_child(node)
		for slot: int in batch.size():
			var head: Head = batch[slot]
			head.multimesh = node.multimesh
			head.slot = slot
			heads.append(head)
			var key: String = (
				"%s/%d/%d" % [head.junction.region, head.junction.id, head.approach.stage]
			)
			if not by_stage.has(key):
				var stage := Stage.new()
				stage.junction = head.junction
				stage.approach = head.approach
				by_stage[key] = stage
				_stages.append(stage)
			by_stage[key].heads.append(head)
	if posts:
		_stand_posts(mesh, cells)
	refresh()


## The posts under every head, one body a plan cell of `cells`.
func _stand_posts(mesh: Mesh, cells: PropCellProfile) -> void:
	var post: AABB = PropBatch.post_of(mesh)
	if not post.has_volume():
		push_error("SignalHeads: %s stands on no post; the heads do not collide" % MESH_NAME)
		return
	var transforms: Array[Transform3D] = []
	for head: Head in heads:
		transforms.append(head.at)
	for body: StaticBody3D in PropBatch.posts(post, transforms, MESH_NAME + "_posts", cells):
		add_child(body)


func _physics_process(_delta: float) -> void:
	var began: int = PerfClock.begin()
	refresh()
	PerfClock.end(PerfClock.Slot.SIGNALS, began)


## Write each stage's light into its heads where it changed since the last write.
func refresh() -> void:
	var clock: float = controller.clock_s
	var table: SignalPlanProfile = controller.profile
	for stage: Stage in _stages:
		var now: int = SignalController.light_at(stage.junction, stage.approach, clock, table)
		if now == stage.light:
			continue
		stage.light = now
		var datum := Color(0.0, 0.0, 0.0, float(now))
		for head: Head in stage.heads:
			head.light = now
			head.multimesh.set_instance_custom_data(head.slot, datum)


## The light head `index` was last WRITTEN — the datum `refresh` set into its
## `INSTANCE_CUSTOM`, never a recomputation. ⚠️ Not read back from the
## `MultiMesh`: headless, the dummy renderer returns `Color()` (alpha 1, RED) for
## every slot, so a readback would grade the dummy. The frames grade the shader.
func light_of(index: int) -> int:
	return heads[index].light


## The head for one placement, or null where the plan does not hold its
## approach at the junction and stage the ETL bound it to.
func _resolve(raw: Dictionary, region: String, graph: RoadGraph) -> Head:
	if String(raw.get("mesh", "")) != MESH_NAME:
		return null
	var edge: int = graph.edge_id_in(region, int(raw.get("edge", -1)))
	if edge < 0:
		return null
	var approach: SignalPlan.Approach = controller.plan.approach_on(
		edge, bool(raw.get("along", false))
	)
	if approach == null:
		return null
	var junction: SignalPlan.Junction = controller.plan.junctions[approach.junction]
	if (
		junction.region != region
		or junction.id != int(raw.get("junction", -1))
		or approach.stage != int(raw.get("stage", -1))
	):
		return null
	var head := Head.new()
	head.junction = junction
	head.approach = approach
	return head


func _library_mesh(path: String) -> Mesh:
	var packed := load(path) as PackedScene
	if packed == null:
		push_error("SignalHeads: library %s did not load as a scene" % path)
		return null
	var library: Node = packed.instantiate()
	var found := library.find_child(MESH_NAME, true, false) as MeshInstance3D
	var mesh: Mesh = found.mesh if found != null else null
	library.free()
	if mesh == null:
		push_error("SignalHeads: library %s holds no %s mesh" % [path, MESH_NAME])
	return mesh
