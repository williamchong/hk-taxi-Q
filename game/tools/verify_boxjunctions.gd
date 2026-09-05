## Checks the generated yellow box junctions against the data contract, headless.
##
## `P3-18` delivers TD's published box polygons as geometry rather than as paint
## on the ribbon, and the facts that decision rests on are engine-side: whether
## the importer dispatched the shader on the material name, whether it built a
## collider it must *not* have, and — the one that matters most — whether every
## triangle still faces the sky. Run:
##
##     godot --headless --path game --script res://tools/verify_boxjunctions.gd
##
## Exits non-zero if the boxes are present and fail any check.
##
## ⚠️ **Absence is a pass, and that is not a loophole** — `verify_arrows.gd`'s
## paragraph, unchanged: a city whose estate publishes no box polygons ships
## none and `city.json` names null. What stops that becoming a silent skip is
## `verify_city.gd`, whose `_check_documents` asserts a *named* box-junction
## asset exists and matches the path `generated_layer.gd`'s table gives it.
extends SceneTree

const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")

## One primitive, so the whole region's boxes cost one draw call — the rule the
## road surface, the tiles, the tramway and the arrows are all held to.
const SURFACES: int = 1

## The material the boxes must end up with, mirroring `SHADERS` in
## `tools/generated_scene_import.gd` and `BOXJUNCTIONS_MATERIAL` in
## `etl/pipeline/boxjunctions.py`.
##
## Checked because the dispatch has **no failing state**: boxes that kept their
## imported `BaseMaterial3D` would be the right hatching on the right junctions
## in whatever colour the importer chose, and nothing else here would notice.
const BOXJUNCTIONS_MATERIAL: String = "res://tuning/boxjunctions.tres"


func _init() -> void:
	if not GeneratedLayer.is_present(GeneratedLayer.BOXJUNCTIONS):
		print(
			(
				"  skip  no %s shipped for this region"
				% GeneratedLayer.noun(GeneratedLayer.BOXJUNCTIONS)
			)
		)
		quit(0)
		return

	var packed: PackedScene = GeneratedLayer.load_layer(GeneratedLayer.BOXJUNCTIONS)
	if packed == null:
		# Present but unloadable, which is not the same as absent — the hint
		# about rebuilding would be the wrong advice here.
		printerr(
			(
				"  FAIL  %s exists but did not load as a scene"
				% GeneratedLayer.path(GeneratedLayer.BOXJUNCTIONS)
			)
		)
		quit(1)
		return

	var scene_root: Node3D = packed.instantiate()
	var problems: PackedStringArray = _check(scene_root)
	# Instantiated outside the tree, so nothing else will free it — and a
	# headless run that leaks buries its own result under exit warnings.
	scene_root.free()
	for problem: String in problems:
		printerr("  FAIL  ", problem)
	if problems.is_empty():
		print("  ok    ", GeneratedLayer.path(GeneratedLayer.BOXJUNCTIONS))
	quit(1 if not problems.is_empty() else 0)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []

	var mesh: ArrayMesh = MeshContract.single_primitive(scene_root, SURFACES, problems)
	if mesh == null:
		return problems

	for surface: int in mesh.get_surface_count():
		var where: String = "surface %d" % surface
		# `false`: this mesh ships no `COLOR_0` on purpose — see
		# `BOXJUNCTIONS_MATERIAL` above and `config.BoxJunctions`. Every other
		# guarantee in `check_surface` still applies, the no-texture one
		# especially.
		problems.append_array(MeshContract.check_surface(mesh, surface, where, false))
		problems.append_array(
			MeshContract.check_shader_material(mesh, surface, where, BOXJUNCTIONS_MATERIAL)
		)
		problems.append_array(MeshContract.check_faces_up(mesh, surface, where, "the boxes"))

	problems.append_array(_check_has_no_collision(scene_root))
	return problems


## Paint must **not** collide, for the reason the arrows must not.
##
## Sharper again here: the hatch crosses the middle of every boxed junction, so
## a collider would be a 12 mm step every vehicle in the region crosses at speed
## while turning — and the whole guard against it is the absence of a `-col`
## suffix in one string in `boxjunctions.py`.
func _check_has_no_collision(scene_root: Node3D) -> PackedStringArray:
	return MeshContract.check_no_collision(
		scene_root, "the box junctions", "BOXJUNCTIONS_MESH_NAME in etl/pipeline/boxjunctions.py"
	)
