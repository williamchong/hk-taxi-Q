## Checks the generated turn arrows against the data contract, headless.
##
## `P3-15` delivers TD's published marking symbols as geometry rather than as
## paint on the ribbon, and the facts that decision rests on are engine-side:
## whether the importer dispatched the shader on the material name, whether it
## built a collider it must *not* have, and — the one that matters most —
## whether every triangle still faces the sky. Run:
##
##     godot --headless --path game --script res://tools/verify_arrows.gd
##
## Exits non-zero if the arrows are present and fail any check.
##
## ⚠️ **Absence is a pass, and that is not a loophole.** A city whose estate
## publishes no marking symbols ships none and `city.json` names null, so this
## cannot treat a missing asset as a failure without failing every such city.
## What stops that becoming a silent skip is `verify_city.gd`, whose
## `_check_documents` asserts a *named* arrows asset exists and matches this
## file's constant — so a manifest naming `arrows.glb` with the file gone fails
## there. ⚠️ `verify_tramway.gd` records that its version of that
## cross-reference was written before the check existed and stood wrong for a
## while. This one was written with it; if this comment is edited, go and look.
extends SceneTree

const GeneratedArrows = preload("res://scripts/city/generated_arrows.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")

## One primitive, so the whole region's arrows cost one draw call — the rule the
## road surface, the tiles and the tramway are all held to.
const SURFACES: int = 1

## The material the arrows must end up with, mirroring `SHADERS` in
## `tools/generated_scene_import.gd` and `ARROWS_MATERIAL` in
## `etl/pipeline/arrows.py`.
##
## Checked because the dispatch has **no failing state**: arrows that kept their
## imported `BaseMaterial3D` would be the right glyphs in the right places in
## whatever colour the importer chose, and nothing else here would notice.
const ARROWS_MATERIAL: String = "res://tuning/arrows.tres"


func _init() -> void:
	if not GeneratedArrows.is_present():
		print("  skip  no turn arrows shipped for this region")
		quit(0)
		return

	var packed: PackedScene = GeneratedArrows.load_arrows()
	if packed == null:
		# Present but unloadable, which is not the same as absent — the hint
		# about rebuilding would be the wrong advice here.
		printerr("  FAIL  %s exists but did not load as a scene" % GeneratedArrows.PATH)
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
		print("  ok    ", GeneratedArrows.PATH)
	quit(1 if not problems.is_empty() else 0)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []

	var mesh: ArrayMesh = MeshContract.single_primitive(scene_root, SURFACES, problems)
	if mesh == null:
		return problems

	for surface: int in mesh.get_surface_count():
		var where: String = "surface %d" % surface
		# `false`: this mesh ships no `COLOR_0` on purpose — see `ARROWS_MATERIAL`
		# above and `config.Arrows`. Every other guarantee in `check_surface`
		# still applies, the no-texture one especially.
		problems.append_array(MeshContract.check_surface(mesh, surface, where, false))
		problems.append_array(
			MeshContract.check_shader_material(mesh, surface, where, ARROWS_MATERIAL)
		)
		problems.append_array(MeshContract.check_faces_up(mesh, surface, where, "the arrows"))

	problems.append_array(_check_has_no_collision(scene_root))
	return problems


## Paint must **not** collide, for the reason the tramway must not.
##
## Sharper here than there: an arrow lies flat across a lane the car is meant to
## drive along, so a collider would be a 15 mm step every vehicle in the region
## crosses at speed — and the whole guard against it is the absence of a `-col`
## suffix in one string in `arrows.py`.
func _check_has_no_collision(scene_root: Node3D) -> PackedStringArray:
	return MeshContract.check_no_collision(
		scene_root, "the arrows", "ARROWS_MESH_NAME in etl/pipeline/arrows.py"
	)
