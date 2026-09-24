## Checks the generated harbour water against the data contract, headless.
##
## The world's water (2026-09-25, the user's call) is the basemap's sea as one
## flat mesh at sea level, and the facts it rests on are engine-side: whether
## the importer dispatched the material on the glTF name, whether it built a
## collider it must *not* have, whether every triangle faces the sky, and
## whether the plane sits at the level `basemap.json` publishes — a plane that
## drifted from `water_level_m` sits above the quay or under the seabed the
## tile stage sank for it, and renders fine either way. Run:
##
##     godot --headless --path game --script res://tools/verify_water.gd
##
## Exits non-zero if the water is present and fails any check.
##
## ⚠️ **Absence is a pass, and that is not a loophole** — `verify_tramway.gd`'s
## paragraph, unchanged: a region whose frame holds no shoreline ships none and
## `city.json` names null. What stops that becoming a silent skip is
## `verify_city.gd`, whose `_check_documents` asserts a *named* water asset
## exists and matches `generated_layer.gd`'s path for it.
extends SceneTree

const GeneratedBasemap = preload("res://scripts/city/generated_basemap.gd")
const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")

## One primitive, so the whole region's sea costs one draw call — the rule the
## tramway and the road marks are held to.
const SURFACES: int = 1

## The material the water must end up with, mirroring `SHADERS` in
## `tools/generated_scene_import.gd` and `WATER_MATERIAL` in
## `etl/pipeline/basemap.py`.
##
## Checked because the dispatch has **no failing state**: a plane that kept its
## imported `BaseMaterial3D` draws the right blue at 0.9 roughness — matte, pale,
## water that reads as painted ground — and nothing else here would notice.
const WATER_MATERIAL: String = "res://tuning/water.tres"

## How far a vertex may sit from `water_level_m`. Compression is off
## project-wide (`Q82`), so this is float32 at a few metres, not slack.
const LEVEL_TOLERANCE_M: float = 0.005


func _init() -> void:
	if not GeneratedLayer.is_present(GeneratedLayer.WATER):
		print("  skip  no %s shipped for this region" % GeneratedLayer.noun(GeneratedLayer.WATER))
		quit(0)
		return

	var packed: PackedScene = GeneratedLayer.load_layer(GeneratedLayer.WATER)
	if packed == null:
		printerr(
			(
				"  FAIL  %s exists but did not load as a scene"
				% GeneratedLayer.path(GeneratedLayer.WATER)
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
		print("  ok    ", GeneratedLayer.path(GeneratedLayer.WATER))
	quit(1 if not problems.is_empty() else 0)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []
	var mesh: ArrayMesh = MeshContract.single_primitive(scene_root, SURFACES, problems)
	if mesh == null:
		return problems

	for surface: int in mesh.get_surface_count():
		var where: String = "water surface %d" % surface
		# `true`: the colour rides on `COLOR_0` from `materials:` (`Q33`).
		problems.append_array(MeshContract.check_surface(mesh, surface, where, true))
		problems.append_array(
			MeshContract.check_shader_material(mesh, surface, where, WATER_MATERIAL)
		)
		problems.append_array(MeshContract.check_faces_up(mesh, surface, where, "the water"))

	problems.append_array(_check_level(mesh))
	problems.append_array(
		MeshContract.check_no_collision(
			scene_root, "the water", "WATER_NAME in etl/pipeline/basemap.py"
		)
	)
	return problems


## The plane is flat, at the level the basemap publishes. Both halves matter: a
## flat plane at the wrong height is the quay flooded or the sea drained, and a
## plane at the right mean height that is not flat is the sheets' terrain noise
## the sink exists to remove, back on the water.
func _check_level(mesh: ArrayMesh) -> PackedStringArray:
	var document: Dictionary = GeneratedBasemap.load_basemap()
	if document.is_empty():
		return ["water shipped but %s did not load" % GeneratedBasemap.path()]
	if document.get("water_level_m") == null:
		return ["%s publishes no water_level_m to hold the plane to" % GeneratedBasemap.path()]
	var level: float = float(document["water_level_m"])
	var box: AABB = mesh.get_aabb()
	var problems: PackedStringArray = []
	if box.size.y > LEVEL_TOLERANCE_M:
		problems.append(
			"the water is not flat: %.3f m from its lowest vertex to its highest" % box.size.y
		)
	if absf(box.position.y - level) > LEVEL_TOLERANCE_M:
		problems.append(
			(
				"the water sits at %.3f m, basemap.json publishes water_level_m %.3f"
				% [box.position.y, level]
			)
		)
	return problems
