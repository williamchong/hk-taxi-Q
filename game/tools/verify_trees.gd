## Checks the generated trees against the data contract, headless (`P3-77`).
##
## The library, the join, and the one claim the layer makes that the others do
## not: a trunk collider under every tree, held in one static body per plan
## cell rather than a body per tree. Run:
##
##     godot --headless --path game --script res://tools/verify_trees.gd
##
## Exits non-zero if the trees are present and fail any check. Absence is a pass
## on `verify_water.gd`'s terms: `verify_city.gd` asserts a NAMED asset exists.
extends SceneTree

const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const GeneratedPlacements = preload("res://scripts/city/generated_placements.gd")
const LayerPreview = preload("res://scripts/city/layer_preview.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")
const VerifyLayer = preload("res://tools/verify_layer.gd")

const SURFACES_PER_MESH: int = 1

## Mirrors `SHADERS` in `tools/generated_scene_import.gd` and `TREES_MATERIAL`
## in `etl/pipeline/trees.py`. Checked by path because the fallback is quiet:
## a tree on its imported `BaseMaterial3D` draws pale, not wrong.
const TREES_MATERIAL: String = "res://tuning/trees.tres"


func _init() -> void:
	VerifyLayer.run(self, GeneratedLayer.TREES, _check)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []
	var library: Dictionary[String, Mesh] = MeshContract.library_meshes(
		scene_root, SURFACES_PER_MESH, problems
	)
	if library.is_empty():
		return problems
	for mesh_name: String in library:
		var mesh := library[mesh_name] as ArrayMesh
		for surface: int in mesh.get_surface_count():
			var where: String = "'%s' surface %d" % [mesh_name, surface]
			# `true`: the colours ride `COLOR_0` from `materials:` (`Q33`).
			problems.append_array(MeshContract.check_surface(mesh, surface, where, true))
			problems.append_array(
				MeshContract.check_shader_material(mesh, surface, where, TREES_MATERIAL)
			)
	var path: String = GeneratedLayer.placements_path(GeneratedLayer.TREES)
	problems.append_array(
		GeneratedPlacements.check_join(path, GeneratedLayer.noun(GeneratedLayer.TREES), library)
	)
	problems.append_array(
		MeshContract.check_no_collision(
			scene_root, "the trees' library", "draw_kind in etl/pipeline/trees.py"
		)
	)
	problems.append_array(_check_trunks(path, library))
	return problems


## Every library mesh has a trunk with a size, and the layer node stands a
## shape under every placement in a body per kind and cell — the count that
## keeps the trees under Jolt's body cap — sized and placed off its own stand.
func _check_trunks(path: String, library: Dictionary[String, Mesh]) -> PackedStringArray:
	var problems: PackedStringArray = []
	var document: Dictionary = GeneratedPlacements.load_placements(
		path, GeneratedLayer.noun(GeneratedLayer.TREES)
	)
	var table: Dictionary = document.get("trunks", {})
	for mesh_name: String in library:
		var trunk: Dictionary = table.get(mesh_name, {})
		if float(trunk.get("radius_m", 0.0)) <= 0.0 or float(trunk.get("height_m", 0.0)) <= 0.0:
			problems.append("'%s' has no sized trunk in %s" % [mesh_name, path])
	if not problems.is_empty():
		return problems

	var cells := load(PropCellProfile.PATH) as PropCellProfile
	if cells == null or GeneratedLayer.TREES not in cells.layers:
		return [
			(
				"%s does not cut the trees, so their trunks stand in one body a kind"
				% PropCellProfile.PATH
			)
		]
	var expected_bodies: Dictionary = {}
	var placements: Array = document.get("placements", []) as Array
	for entry: Dictionary in placements:
		var at: Vector3 = (GeneratedPlacements.placement_of(entry) as Transform3D).origin
		expected_bodies[[String(entry.get("mesh", "")), cells.cell_of(at)]] = true

	# Built out of the tree and `_ready` called by hand: inside `_init` the
	# root has not started, so a node added to it is never readied.
	var node: Node3D = LayerPreview.new()
	node.layer = GeneratedLayer.TREES
	node.trunks = true
	node._ready()
	var bodies: int = 0
	var shapes: Array[CollisionShape3D] = []
	for found: Node in node.find_children("*", "StaticBody3D", true, false):
		bodies += 1
		for child: Node in found.get_children():
			var collision := child as CollisionShape3D
			if collision != null and collision.shape is CylinderShape3D:
				shapes.append(collision)
	if shapes.size() != placements.size():
		problems.append("%d trunk shapes stand under %d trees" % [shapes.size(), placements.size()])
	if bodies != expected_bodies.size():
		problems.append(
			"%d trunk bodies for %d kind-and-cell pairs" % [bodies, expected_bodies.size()]
		)
	if problems.is_empty() and not placements.is_empty():
		problems.append_array(_check_first_trunk(placements[0], table, shapes))
	node.free()
	if problems.is_empty():
		print("  ok    %d trunks in %d bodies" % [shapes.size(), bodies])
	return problems


## The first placement's trunk: its kind's size times the stand's scale, its
## foot on the stand's origin. A count alone passes a trunk left unscaled or
## centred on the ground, half of it buried.
func _check_first_trunk(
	entry: Dictionary, table: Dictionary, shapes: Array[CollisionShape3D]
) -> PackedStringArray:
	var at: Transform3D = GeneratedPlacements.placement_of(entry)
	var trunk: Dictionary = table[String(entry.get("mesh", ""))]
	var grown: float = at.basis.get_scale().y
	var radius: float = float(trunk["radius_m"]) * grown
	var height: float = float(trunk["height_m"]) * grown
	var centre: Vector3 = at.origin + Vector3(0.0, height * 0.5, 0.0)
	for collision: CollisionShape3D in shapes:
		var shape := collision.shape as CylinderShape3D
		if collision.position.distance_to(centre) < 1e-3:
			if absf(shape.radius - radius) > 1e-4 or absf(shape.height - height) > 1e-4:
				return [
					(
						"the trunk at %s is %.3f x %.3f m, its stand says %.3f x %.3f m"
						% [at.origin, shape.radius, shape.height, radius, height]
					)
				]
			return []
	return [
		"no trunk is centred %.2f m over the first tree's foot at %s" % [height * 0.5, at.origin]
	]
