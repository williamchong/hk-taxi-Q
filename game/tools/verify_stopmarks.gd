## Checks the generated stop and stand markings against the data contract,
## headless.
##
## `P3-89` delivers TD's surveyed bus stop, stand and tram stop paint as geometry, on the terms
## `verify_boxjunctions.gd` states for the boxes: whether the importer dispatched
## the shader on the material name, whether it built a collider it must *not*
## have, and whether every triangle still faces the sky. Run:
##
##     godot --headless --path game --script res://tools/verify_stopmarks.gd
##
## Exits non-zero if the markings are present and fail any check.
##
## ⚠️ **Absence is a pass, and that is not a loophole** — `verify_arrows.gd`'s
## paragraph, unchanged. `verify_city.gd`'s `_check_documents` is what asserts a
## *named* asset exists.
extends SceneTree

const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const VerifyLayer = preload("res://tools/verify_layer.gd")
const MeshContract = preload("res://tools/mesh_contract.gd")

## One surface a mesh, so a cell of one paint costs one draw call.
##
## ⚠️ **One mesh a kind a plan CELL** (`Q135`), so the engine can cull the layer. A mesh is named
## `<kind>_c<column>_r<row>` (`meshbuild.cell_name`); its glTF material is still
## the bare kind, which is what the importer dispatches on.
const SURFACES_PER_KIND: int = 1

## The material each kind must end up with, mirroring `SHADERS` in
## `tools/generated_scene_import.gd` and `KINDS` in `etl/pipeline/stopmarks.py`.
##
## 🔴 **They are the box junctions' and the road marks' own `.tres`, on purpose**
## (`verify_crossings.gd`): one paint has one dial. A kind handed the other's
## material is a yellow bus stop that renders perfectly, which is why this is
## checked per kind.
const KIND_MATERIALS: Dictionary[String, String] = {
	"stopmarks_yellow": "res://tuning/boxjunctions.tres",
	"stopmarks_white": "res://tuning/roadmarks.tres",
}


func _init() -> void:
	VerifyLayer.run(self, GeneratedLayer.STOPMARKS, _check)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []

	# One `MeshInstance3D` a paint a plan cell, each named for its kind and its
	# cell — `verify_railings`' shape, because `MeshContract.library_meshes` has
	# no per-name material to check against.
	var instances: Array[Node] = scene_root.find_children("*", "MeshInstance3D", true, false)
	if instances.is_empty():
		problems.append("no MeshInstance3D in the stop markings scene")
		return problems

	for node: Node in instances:
		var instance := node as MeshInstance3D
		# 🔴 The kind comes off the mesh NAME, never off its material: read from
		# the material, a white box handed the yellow checks out against itself.
		var kind: String = _kind_of(String(instance.name))
		if not KIND_MATERIALS.has(kind):
			problems.append(
				(
					"mesh '%s' is not a cell of a known stop marking kind. " % instance.name
					+ "KIND_MATERIALS here, SHADERS in generated_scene_import.gd and "
					+ "KINDS in etl/pipeline/stopmarks.py move together."
				)
			)
			continue

		var mesh := instance.mesh as ArrayMesh
		if mesh == null:
			problems.append("'%s' carries no ArrayMesh" % instance.name)
			continue
		if mesh.get_surface_count() != SURFACES_PER_KIND:
			problems.append(
				(
					"'%s' has %d surfaces, expected %d"
					% [instance.name, mesh.get_surface_count(), SURFACES_PER_KIND]
				)
			)

		for surface: int in mesh.get_surface_count():
			var where: String = "%s surface %d" % [instance.name, surface]
			# `false`: no `COLOR_0`, as the boxes ship none.
			problems.append_array(MeshContract.check_surface(mesh, surface, where, false))
			problems.append_array(
				MeshContract.check_shader_material(mesh, surface, where, KIND_MATERIALS[kind])
			)
			problems.append_array(
				MeshContract.check_faces_up(mesh, surface, where, "the stop markings")
			)

	problems.append_array(
		MeshContract.check_no_collision(
			scene_root, "the stop markings", "KINDS in etl/pipeline/stopmarks.py"
		)
	)
	return problems


## The kind a cell's mesh is of — `meshbuild.cell_name`'s `<kind>_c<column>_r<row>`
## read backwards — or `""` for a name that is not a cell's. A column or a row is
## negative west or north of the origin.
func _kind_of(mesh_name: String) -> String:
	var cell := RegEx.create_from_string("^(.+)_c-?\\d+_r-?\\d+$")
	var found: RegExMatch = cell.search(mesh_name)
	return "" if found == null else found.get_string(1)
