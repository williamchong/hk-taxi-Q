extends SceneTree
## Checks `stops.glb` — the authored flags and shelters at published stops
## (`P3-94`, `Q242`) — as the engine loads it: a library on the signs' material,
## stood by `stops_placements.json`, with a collider under each pole and each
## shelter post, and none under a flag or a shelter's roof.
##
## Run through `tools/check.sh`; its exit code is the result.

const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const VerifyLayer = preload("res://tools/verify_layer.gd")
const GeneratedPlacements = preload("res://scripts/city/generated_placements.gd")
const MeshContract = preload("res://tools/mesh_contract.gd")

## One surface a library mesh: `stops.py` builds each with one `ColouredBuilder`.
const SURFACES_PER_MESH: int = 1

## The signs' own `.tres`: `stops.py` names its meshes' material `signs`, and
## `SHADERS` in `generated_scene_import.gd` maps it.
const STOPS_MATERIAL: String = "res://tuning/signs.tres"

## The shelter's roof must NOT stand on a post — a cylinder its whole footprint,
## across the lane beside the track. Its two posts are their own mesh and must.
const UNPOSTED: String = "tram_shelter"
const POSTED: String = "tram_post"

const PropBatch = preload("res://scripts/city/prop_batch.gd")


func _init() -> void:
	VerifyLayer.run(self, GeneratedLayer.STOPS, _check)


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
			problems.append_array(MeshContract.check_surface(mesh, surface, where, true))
			problems.append_array(
				MeshContract.check_shader_material(mesh, surface, where, STOPS_MATERIAL)
			)
	if library.has(UNPOSTED) and PropBatch.post_of(library[UNPOSTED]).has_volume():
		problems.append(
			(
				"'%s' stands on a post, so the engine puts a collider in the lane beside the track"
				% UNPOSTED
			)
		)
	if library.has(UNPOSTED) != library.has(POSTED):
		problems.append("'%s' and '%s' ship together or not at all" % [UNPOSTED, POSTED])
	if library.has(POSTED) and not PropBatch.post_of(library[POSTED]).has_volume():
		problems.append("'%s' stands on no post, so a shelter is driven through" % POSTED)
	problems.append_array(
		GeneratedPlacements.check_join(
			GeneratedLayer.placements_path(GeneratedLayer.STOPS),
			GeneratedLayer.noun(GeneratedLayer.STOPS),
			library
		)
	)
	problems.append_array(
		MeshContract.check_no_collision(
			scene_root, "the stop furniture", "library.write in etl/pipeline/stops.py"
		)
	)
	problems.append_array(VerifyLayer.check_posts(GeneratedLayer.STOPS, library))
	return problems
