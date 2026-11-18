## Checks the generated pedestrian lines against the data contract, headless
## (`P3-101`, `Q250`).
##
## A mesh a plan cell, and the claims a frame cannot check: that the importer
## dispatched the material, that every ribbon faces up — one wound down draws
## nothing under `cull_back` — and that none of it collides. Run:
##
##     godot --headless --path game --script res://tools/verify_paths.gd
##
## Exits non-zero if the lines are present and fail any check. Absence is a
## pass on `verify_water.gd`'s terms: `verify_city.gd` asserts a NAMED asset
## exists.
extends SceneTree

const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const VerifyLayer = preload("res://tools/verify_layer.gd")
const MeshContract = preload("res://tools/mesh_contract.gd")

## One primitive a cell, so a cell in view costs one draw call.
const SURFACES: int = 1

## Mirrors `SHADERS` in `tools/generated_scene_import.gd` and `PATHS_MATERIAL`
## in `etl/pipeline/paths.py`. Checked by path because the fallback is quiet:
## a ribbon on its imported `BaseMaterial3D` draws pale.
const PATHS_MATERIAL: String = "res://tuning/paths.tres"


func _init() -> void:
	VerifyLayer.run(self, GeneratedLayer.PATHS, _check)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []
	var cells: Dictionary[String, Mesh] = MeshContract.library_meshes(
		scene_root, SURFACES, problems
	)
	for cell: String in cells:
		var mesh: Mesh = cells[cell]
		for surface: int in mesh.get_surface_count():
			var where: String = "%s surface %d" % [cell, surface]
			# `true`: the colour rides `COLOR_0` from `materials:` (`Q33`).
			problems.append_array(MeshContract.check_surface(mesh, surface, where, true))
			problems.append_array(
				MeshContract.check_shader_material(mesh, surface, where, PATHS_MATERIAL)
			)
			problems.append_array(MeshContract.check_faces_up(mesh, surface, where, "the lines"))
	# A ribbon is driven over: a body here is a 6 cm step under every wheel.
	problems.append_array(
		MeshContract.check_no_collision(
			scene_root, "the pedestrian lines", "PATHS_MESH_NAME in etl/pipeline/paths.py"
		)
	)
	return problems
