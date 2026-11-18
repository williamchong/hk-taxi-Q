## Checks the generated signboards against the data contract, headless
## (`P3-103`, `Q260`).
##
## A mesh a plan cell, and the claims a frame cannot check: that the importer
## dispatched the material — a board left on its imported `BaseMaterial3D`
## draws its colour and never lights at night — and that none of it collides.
## Run:
##
##     godot --headless --path game --script res://tools/verify_signboards.gd
##
## Exits non-zero if the boards are present and fail any check. Absence is a
## pass on `verify_water.gd`'s terms: `verify_city.gd` asserts a NAMED asset
## exists. A board's winding against its normals is the ETL's to publish
## (`facing_away` in `signboards.json`, held at 0 by `test_signboards.py`): a
## box faces every way, so `check_faces_up` has nothing to say about it.
extends SceneTree

const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const VerifyLayer = preload("res://tools/verify_layer.gd")
const MeshContract = preload("res://tools/mesh_contract.gd")

## One primitive a cell, so a cell in view costs one draw call.
const SURFACES: int = 1

## Mirrors `SHADERS` in `tools/generated_scene_import.gd` and
## `SIGNBOARDS_MATERIAL` in `etl/pipeline/signboards.py`.
const SIGNBOARDS_MATERIAL: String = "res://tuning/signboards.tres"

## The lettering (`P3-103` step 2): its own primitive a cell, named
## `signboards_text_<cell>` (`TEXT_MESH_NAME` in `etl/pipeline/signboard_text.py`),
## on a material duplicated per region to hold the atlas, so checked through its
## shader as `verify_signs.gd` checks the signs' lettering.
const TEXT_PREFIX: String = "signboards_text"
const TEXT_MATERIAL: String = "res://tuning/signboards_text.tres"
const TEXT_SHADER: String = "res://assets/shaders/signboards_text.gdshader"


func _init() -> void:
	VerifyLayer.run(self, GeneratedLayer.SIGNBOARDS, _check)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []
	var cells: Dictionary[String, Mesh] = MeshContract.library_meshes(
		scene_root, SURFACES, problems
	)
	for cell: String in cells:
		var mesh: Mesh = cells[cell]
		if cell.begins_with(TEXT_PREFIX):
			problems.append_array(_check_lettering(mesh, cell))
			continue
		for surface: int in mesh.get_surface_count():
			var where: String = "%s surface %d" % [cell, surface]
			# `true`: the colour and the lit-face marker ride `COLOR_0`.
			problems.append_array(MeshContract.check_surface(mesh, surface, where, true))
			problems.append_array(
				MeshContract.check_shader_material(mesh, surface, where, SIGNBOARDS_MATERIAL)
			)
	# A blade hangs over the pavement above head height; a body here is a
	# ceiling a jump hits.
	problems.append_array(
		MeshContract.check_no_collision(
			scene_root, "the signboards", "SIGNBOARDS_MESH_NAME in etl/pipeline/signboards.py"
		)
	)
	return problems


## A glyph whose texture never arrived samples black and the scissor cuts it
## away; one whose material was not dispatched draws as a solid block. Neither
## moves a triangle count.
func _check_lettering(mesh: Mesh, cell: String) -> PackedStringArray:
	var problems: PackedStringArray = []
	for surface: int in mesh.get_surface_count():
		var where: String = "%s surface %d" % [cell, surface]
		if not (mesh.surface_get_format(surface) & Mesh.ARRAY_FORMAT_TEX_UV):
			problems.append("%s carries no UVs" % where)
		problems.append_array(
			MeshContract.check_surface(
				mesh, surface, where, true, GeneratedLayer.SIGNBOARDS_TEXT_ATLAS_BUDGET_PX
			)
		)
		problems.append_array(
			MeshContract.check_shader_source(mesh, surface, where, TEXT_SHADER, TEXT_MATERIAL)
		)
	return problems
