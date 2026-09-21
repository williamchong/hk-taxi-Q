## Checks the generated pedestrian-crossing stripes against the data contract,
## headless.
##
## `P3-35g2` delivers TD's surveyed crossing stripes as geometry, on the terms
## `verify_boxjunctions.gd` states for the boxes: whether the importer dispatched
## the shader on the material name, whether it built a collider it must *not*
## have, and whether every triangle still faces the sky. Run:
##
##     godot --headless --path game --script res://tools/verify_crossings.gd
##
## Exits non-zero if the crossings are present and fail any check.
##
## ⚠️ **Absence is a pass, and that is not a loophole** — `verify_arrows.gd`'s
## paragraph, unchanged. `verify_city.gd`'s `_check_documents` is what asserts a
## *named* crossings asset exists.
extends SceneTree

const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")

## One surface a mesh, so a cell of one paint costs one draw call.
##
## ⚠️ **One mesh a kind a plan CELL since `P3-42` (`Q135`), no longer one a
## kind**, so the engine can cull the layer. A mesh is named
## `<kind>_c<column>_r<row>` (`meshbuild.cell_name`); its glTF material is still
## the bare kind, which is what the importer dispatches on.
const SURFACES_PER_KIND: int = 1

## The material each kind must end up with, mirroring `SHADERS` in
## `tools/generated_scene_import.gd` and `SIGNAL` / `ZEBRA` in
## `etl/pipeline/crossings.py`.
##
## 🔴 **They are the box junctions' and the road marks' own `.tres`, on purpose**:
## a light-signal crossing is painted in the yellow a box is and a zebra in the
## white a stop line is, and one paint has one dial. A kind handed the other's
## material is a yellow zebra that renders perfectly, which is why this is
## checked per kind.
const KIND_MATERIALS: Dictionary[String, String] = {
	"crossings_signal": "res://tuning/boxjunctions.tres",
	"crossings_zebra": "res://tuning/roadmarks.tres",
}


func _init() -> void:
	if not GeneratedLayer.is_present(GeneratedLayer.CROSSINGS):
		print(
			"  skip  no %s shipped for this region" % GeneratedLayer.noun(GeneratedLayer.CROSSINGS)
		)
		quit(0)
		return

	var packed: PackedScene = GeneratedLayer.load_layer(GeneratedLayer.CROSSINGS)
	if packed == null:
		printerr(
			(
				"  FAIL  %s exists but did not load as a scene"
				% GeneratedLayer.path(GeneratedLayer.CROSSINGS)
			)
		)
		quit(1)
		return

	var scene_root: Node3D = packed.instantiate()
	var problems: PackedStringArray = _check(scene_root)
	scene_root.free()
	for problem: String in problems:
		printerr("  FAIL  ", problem)
	if problems.is_empty():
		print("  ok    ", GeneratedLayer.path(GeneratedLayer.CROSSINGS))
	quit(1 if not problems.is_empty() else 0)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []

	# One `MeshInstance3D` a paint a plan cell, each named for its kind and its
	# cell — `verify_railings`' shape, because `MeshContract.library_meshes` has
	# no per-name material to check against.
	var instances: Array[Node] = scene_root.find_children("*", "MeshInstance3D", true, false)
	if instances.is_empty():
		problems.append("no MeshInstance3D in the crossings scene")
		return problems

	for node: Node in instances:
		var instance := node as MeshInstance3D
		# 🔴 The kind comes off the mesh NAME, never off its material: read from
		# the material, a zebra handed the boxes' yellow checks out against itself.
		var kind: String = _kind_of(String(instance.name))
		if not KIND_MATERIALS.has(kind):
			problems.append(
				(
					"mesh '%s' is not a cell of a known crossing kind. " % instance.name
					+ "KIND_MATERIALS here, SHADERS in generated_scene_import.gd and "
					+ "KINDS in etl/pipeline/crossings.py move together."
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
				MeshContract.check_faces_up(mesh, surface, where, "the crossing stripes")
			)

	problems.append_array(
		MeshContract.check_no_collision(
			scene_root, "the crossings", "SIGNAL and ZEBRA in etl/pipeline/crossings.py"
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
