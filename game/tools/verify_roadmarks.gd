## Checks the generated stop and give-way lines against the data contract, headless.
##
## `P3-23` delivers TD's published transverse markings as geometry rather than
## as paint on the ribbon, and the facts that decision rests on are engine-side:
## whether the importer dispatched the shader on the material name, whether it
## built a collider it must *not* have, and — the one that matters most —
## whether every triangle still faces the sky. Run:
##
##     godot --headless --path game --script res://tools/verify_roadmarks.gd
##
## Exits non-zero if the markings are present and fail any check.
##
## ⚠️ **Absence is a pass, and that is not a loophole** — `verify_arrows.gd`'s
## paragraph, unchanged: a city whose estate publishes no transverse markings
## ships none and `city.json` names null. What stops that becoming a silent skip
## is `verify_city.gd`, whose `_check_documents` asserts a *named* road-marking
## asset exists and matches this file's constant.
extends SceneTree

const GeneratedRoadMarks = preload("res://scripts/city/generated_roadmarks.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")

## One primitive, so the whole region's markings cost one draw call — the rule
## the road surface, the tiles, the tramway, the arrows and the boxes are all
## held to. All three published codes are the same white paint, so they share one
## material and there is nothing here to split.
const SURFACES: int = 1

## The material the markings must end up with, mirroring `SHADERS` in
## `tools/generated_scene_import.gd` and `ROADMARKS_MATERIAL` in
## `etl/pipeline/roadmarks.py`.
##
## Checked because the dispatch has **no failing state**: markings that kept
## their imported `BaseMaterial3D` would be the right bars across the right
## approaches in whatever colour the importer chose, and nothing else here would
## notice.
const ROADMARKS_MATERIAL: String = "res://tuning/roadmarks.tres"


func _init() -> void:
	if not GeneratedRoadMarks.is_present():
		print("  skip  no road markings shipped for this region")
		quit(0)
		return

	var packed: PackedScene = GeneratedRoadMarks.load_roadmarks()
	if packed == null:
		# Present but unloadable, which is not the same as absent — the hint
		# about rebuilding would be the wrong advice here.
		printerr("  FAIL  %s exists but did not load as a scene" % GeneratedRoadMarks.PATH)
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
		print("  ok    ", GeneratedRoadMarks.PATH)
	quit(1 if not problems.is_empty() else 0)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []

	var mesh: ArrayMesh = MeshContract.single_primitive(scene_root, SURFACES, problems)
	if mesh == null:
		return problems

	for surface: int in mesh.get_surface_count():
		var where: String = "surface %d" % surface
		# `false`: this mesh ships no `COLOR_0` on purpose — see
		# `ROADMARKS_MATERIAL` above and `config.RoadMarks`. Every other
		# guarantee in `check_surface` still applies, the no-texture one
		# especially.
		problems.append_array(MeshContract.check_surface(mesh, surface, where, false))
		problems.append_array(
			MeshContract.check_shader_material(mesh, surface, where, ROADMARKS_MATERIAL)
		)
		problems.append_array(MeshContract.check_faces_up(mesh, surface, where, "the markings"))

	problems.append_array(_check_has_no_collision(scene_root))
	return problems


## Paint must **not** collide, for the reason the arrows and the boxes must not.
##
## Sharper again here: a stop line runs across every signalised approach in the
## region, so a collider would be a 16 mm step the player mounts at every
## junction — while braking, which is the one moment a step under the front
## wheels matters — and the whole guard against it is the absence of a `-col`
## suffix in one string in `roadmarks.py`.
func _check_has_no_collision(scene_root: Node3D) -> PackedStringArray:
	return MeshContract.check_no_collision(
		scene_root, "the road markings", "ROADMARKS_MESH_NAME in etl/pipeline/roadmarks.py"
	)
