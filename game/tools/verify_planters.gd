## Checks the generated roadside planters against the data contract, headless
## (`P3-98`, `Q247`).
##
## A mesh a plan cell and one `-colonly` body beside them, and the two claims a frame
## cannot check: that the importer dispatched the material, and that the body
## is there, is the walls and stops below the planting — a planter that
## imported without it draws exactly the same and a car drives through it. Run:
##
##     godot --headless --path game --script res://tools/verify_planters.gd
##
## Exits non-zero if the planters are present and fail any check. Absence is a
## pass on `verify_water.gd`'s terms: `verify_city.gd` asserts a NAMED asset
## exists.
extends SceneTree

const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const VerifyLayer = preload("res://tools/verify_layer.gd")
const MeshContract = preload("res://tools/mesh_contract.gd")

## One primitive a cell, so a cell in view costs one draw call.
const SURFACES: int = 1

## Mirrors `SHADERS` in `tools/generated_scene_import.gd` and
## `PLANTERS_MATERIAL` in `etl/pipeline/planters.py`. Checked by path because
## the fallback is quiet: a planter on its imported `BaseMaterial3D` draws pale.
const PLANTERS_MATERIAL: String = "res://tuning/planters.tres"

## The body the importer makes of `PLANTERS_COLLIDER_NAME` in
## `etl/pipeline/planters.py`: the node's name, less the suffix it acted on.
const COLLIDER_BODY: String = "planters_collision"


func _init() -> void:
	VerifyLayer.run(self, GeneratedLayer.PLANTERS, _check)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []
	var cells: Dictionary[String, Mesh] = MeshContract.library_meshes(
		scene_root, SURFACES, problems
	)
	var drawn := AABB()
	for cell: String in cells:
		var mesh: Mesh = cells[cell]
		drawn = mesh.get_aabb() if drawn.size == Vector3.ZERO else drawn.merge(mesh.get_aabb())
		for surface: int in mesh.get_surface_count():
			var where: String = "%s surface %d" % [cell, surface]
			# `true`: the colours ride `COLOR_0` from `materials:` (`Q33`).
			problems.append_array(MeshContract.check_surface(mesh, surface, where, true))
			problems.append_array(
				MeshContract.check_shader_material(mesh, surface, where, PLANTERS_MATERIAL)
			)
	problems.append_array(MeshContract.check_collision_only(scene_root, COLLIDER_BODY))
	if problems.is_empty():
		problems.append_array(_check_walls_alone(scene_root, drawn))
	return problems


## The body is the walls and none of the planting: it spans the drawn cells in
## plan and stops short of their top. A collider built from the drawn mesh —
## hedge and all — passes every other check here.
func _check_walls_alone(scene_root: Node3D, drawn: AABB) -> PackedStringArray:
	var shapes: Array[Node] = scene_root.find_children("*", "CollisionShape3D", true, false)
	var faces: PackedVector3Array = (
		((shapes[0] as CollisionShape3D).shape as ConcavePolygonShape3D).get_faces()
	)
	var solid := AABB(faces[0], Vector3.ZERO)
	for point: Vector3 in faces:
		solid = solid.expand(point)
	var problems: PackedStringArray = []
	if solid.end.y >= drawn.end.y:
		(
			problems
			. append(
				(
					"the collider tops out at %.2f m and the drawn planters at %.2f m: it holds the planting"
					% [solid.end.y, drawn.end.y]
				)
			)
		)
	if absf(solid.size.x - drawn.size.x) > 0.01 or absf(solid.size.z - drawn.size.z) > 0.01:
		problems.append(
			(
				"the collider spans %.1f x %.1f m and the drawn planters %.1f x %.1f m"
				% [solid.size.x, solid.size.z, drawn.size.x, drawn.size.z]
			)
		)
	if problems.is_empty():
		print(
			"  ok    walls collide in %d triangles, the planting in none" % int(faces.size() / 3.0)
		)
	return problems
