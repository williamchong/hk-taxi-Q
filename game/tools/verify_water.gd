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
const VerifyLayer = preload("res://tools/verify_layer.gd")
const MeshContract = preload("res://tools/mesh_contract.gd")

## One primitive a mesh, so the whole region's sea costs one draw call and the
## land beside it one more — the rule the tramway and the road marks are held to.
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

## The asset's two meshes by node name: `water_mesh`'s name and
## `LAND_MESH_NAME` in `etl/pipeline/basemap.py`. The land is optional — a
## frame whose every piece of land is some region's tiles ships none.
const WATER_MESH: String = "water"
const LAND_MESH: String = "harbour_land"

## `LAND_MATERIAL`'s `.tres`, as `WATER_MATERIAL` is the water's.
const LAND_MATERIAL: String = "res://tuning/harbour_land.tres"


func _init() -> void:
	VerifyLayer.run(self, GeneratedLayer.WATER, _check)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []
	var meshes: Dictionary[String, Mesh] = MeshContract.library_meshes(
		scene_root, SURFACES, problems
	)
	if not meshes.has(WATER_MESH):
		problems.append("the asset carries no '%s' mesh" % WATER_MESH)
		return problems
	for stray: String in meshes:
		if stray != WATER_MESH and stray != LAND_MESH:
			problems.append("'%s' is neither the water nor the land beside it" % stray)

	var mesh := meshes[WATER_MESH] as ArrayMesh
	for surface: int in mesh.get_surface_count():
		var where: String = "water surface %d" % surface
		# `true`: the colour rides on `COLOR_0` from `materials:` (`Q33`).
		problems.append_array(MeshContract.check_surface(mesh, surface, where, true))
		problems.append_array(
			MeshContract.check_shader_material(mesh, surface, where, WATER_MATERIAL)
		)
		problems.append_array(MeshContract.check_faces_up(mesh, surface, where, "the water"))
	problems.append_array(_check_level(mesh))

	if meshes.has(LAND_MESH):
		problems.append_array(_check_land(meshes[LAND_MESH] as ArrayMesh, mesh))
	problems.append_array(
		MeshContract.check_no_collision(
			scene_root, "the water", "WATER_NAME in etl/pipeline/basemap.py"
		)
	)
	return problems


## The land beside the harbour (`P3-101`): on its own material — on the
## water's it draws waves — standing over the water, and walled to below it.
func _check_land(land: ArrayMesh, water: ArrayMesh) -> PackedStringArray:
	var problems: PackedStringArray = []
	for surface: int in land.get_surface_count():
		var where: String = "land surface %d" % surface
		problems.append_array(MeshContract.check_surface(land, surface, where, true))
		problems.append_array(
			MeshContract.check_shader_material(land, surface, where, LAND_MATERIAL)
		)
	var level: float = water.get_aabb().position.y
	var box: AABB = land.get_aabb()
	if box.end.y <= level:
		problems.append(
			"the land tops out at %.2f m, under the water at %.2f m" % [box.end.y, level]
		)
	if box.position.y >= level:
		problems.append(
			(
				"the land's face stops at %.2f m, over the water at %.2f m: it floats"
				% [box.position.y, level]
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
