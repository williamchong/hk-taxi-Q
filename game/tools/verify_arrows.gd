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
## 🔴 **Since `P5-4` (`Q115`) the asset is a LIBRARY — one flat glyph per `RM`
## code, nose north at the origin — and the city is `arrows_placements.json`.**
## Every mesh check below runs per library mesh, which is every arrow in the
## city checked once; the faces-up check in particular is asked of the glyph as
## drawn, and the pitched stand is graded by the ETL's `inverted` over the stood
## copies, because a rotation is not something an importer can flip. The join
## is graded both ways by `GeneratedPlacements.check_join`, shared with
## `verify_signs.gd` and `verify_lamps.gd`.
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

const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const GeneratedPlacements = preload("res://scripts/city/generated_placements.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")

## One surface per library mesh, so each glyph is one draw call — the rule the
## sign and lamp libraries are held to, and before `P5-4` the merged mesh's:
## one primitive for the region's arrows.
const SURFACES_PER_MESH: int = 1

## The material the arrows must end up with, mirroring `SHADERS` in
## `tools/generated_scene_import.gd` and `ARROWS_MATERIAL` in
## `etl/pipeline/arrows.py`.
##
## Checked because the dispatch has **no failing state**: arrows that kept their
## imported `BaseMaterial3D` would be the right glyphs in the right places in
## whatever colour the importer chose, and nothing else here would notice.
const ARROWS_MATERIAL: String = "res://tuning/arrows.tres"


func _init() -> void:
	if not GeneratedLayer.is_present(GeneratedLayer.ARROWS):
		print("  skip  no %s shipped for this region" % GeneratedLayer.noun(GeneratedLayer.ARROWS))
		quit(0)
		return

	var packed: PackedScene = GeneratedLayer.load_layer(GeneratedLayer.ARROWS)
	if packed == null:
		# Present but unloadable, which is not the same as absent — the hint
		# about rebuilding would be the wrong advice here.
		printerr(
			(
				"  FAIL  %s exists but did not load as a scene"
				% GeneratedLayer.path(GeneratedLayer.ARROWS)
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
		print("  ok    ", GeneratedLayer.path(GeneratedLayer.ARROWS))
	quit(1 if not problems.is_empty() else 0)


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
			# `false`: this mesh ships no `COLOR_0` on purpose — see `ARROWS_MATERIAL`
			# above and `config.Arrows`. Every other guarantee in `check_surface`
			# still applies, the no-texture one especially.
			problems.append_array(MeshContract.check_surface(mesh, surface, where, false))
			problems.append_array(
				MeshContract.check_shader_material(mesh, surface, where, ARROWS_MATERIAL)
			)
			problems.append_array(MeshContract.check_faces_up(mesh, surface, where, "the arrows"))
	problems.append_array(
		GeneratedPlacements.check_join(
			GeneratedLayer.placements_path(GeneratedLayer.ARROWS),
			GeneratedLayer.noun(GeneratedLayer.ARROWS),
			library
		)
	)
	problems.append_array(_check_has_no_collision(scene_root))
	return problems


## Paint must **not** collide, for the reason the tramway must not.
##
## Sharper here than there: an arrow lies flat across a lane the car is meant to
## drive along, so a collider would be a 15 mm step every vehicle in the region
## crosses at speed — and the whole guard against it is the absence of a `-col`
## suffix on the name each library glyph is built under in `arrows.py`.
func _check_has_no_collision(scene_root: Node3D) -> PackedStringArray:
	return MeshContract.check_no_collision(
		scene_root, "the arrows", "glyph_mesh_name in etl/pipeline/arrows.py"
	)
