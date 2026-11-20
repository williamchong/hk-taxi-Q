## Checks TD's generated gantry boards against the data contract, headless
## (`P3-105`, `Q265`).
##
## Two meshes and one `-colonly` body, and the claims a frame cannot check: that
## the importer dispatched both materials — a face left on its imported
## `BaseMaterial3D` loses the sRGB decode, and the steel draws pale — that the
## atlas arrived within its budget, and that the legs alone collide. A board's
## winding is the ETL's to publish (`facing_away` in `direction_signs.json`,
## held at 0 by `test_direction_signs.py`). Run:
##
##     godot --headless --path game --script res://tools/verify_direction_signs.gd
##
## Exits non-zero if the boards are present and fail any check. Absence is a
## pass on `verify_water.gd`'s terms: `verify_city.gd` asserts a NAMED asset
## exists.
extends SceneTree

const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const VerifyLayer = preload("res://tools/verify_layer.gd")
const MeshContract = preload("res://tools/mesh_contract.gd")

## One primitive a mesh, so the steel and the faces cost a draw call each.
const SURFACES: int = 1

## Mirrors `FRAME_MESH_NAME` / `FACE_MESH_NAME` in
## `etl/pipeline/direction_signs.py`, and `SHADERS` / `TEXTURED` in
## `tools/generated_scene_import.gd`.
const FRAME: String = "direction_signs"
const FRAME_MATERIAL: String = "res://tuning/signs.tres"
const FACE: String = "direction_signs_face"
const FACE_MATERIAL: String = "res://tuning/direction_signs_face.tres"
const FACE_SHADER: String = "res://assets/shaders/signs_text.gdshader"

## The body the importer makes of `COLLIDER_NAME`: the node's name, less the
## suffix it acted on.
const COLLIDER_BODY: String = "direction_signs_collision"


func _init() -> void:
	VerifyLayer.run(self, GeneratedLayer.DIRECTION_SIGNS, _check)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []
	var meshes: Dictionary[String, Mesh] = MeshContract.library_meshes(
		scene_root, SURFACES, problems
	)
	for name: String in [FRAME, FACE]:
		if not meshes.has(name):
			problems.append("no '%s' mesh; found %s" % [name, meshes.keys()])
	if not problems.is_empty():
		return problems
	var frame: Mesh = meshes[FRAME]
	var where: String = "%s surface 0" % FRAME
	# `true`: the steel's grey rides `COLOR_0` from `signs.colours`.
	problems.append_array(MeshContract.check_surface(frame, 0, where, true))
	problems.append_array(MeshContract.check_shader_material(frame, 0, where, FRAME_MATERIAL))

	var face: Mesh = meshes[FACE]
	where = "%s surface 0" % FACE
	if not (face.surface_get_format(0) & Mesh.ARRAY_FORMAT_TEX_UV):
		problems.append("%s carries no UVs" % where)
	problems.append_array(
		MeshContract.check_surface(
			face, 0, where, true, GeneratedLayer.DIRECTION_SIGNS_ATLAS_BUDGET_PX
		)
	)
	problems.append_array(
		MeshContract.check_shader_source(face, 0, where, FACE_SHADER, FACE_MATERIAL)
	)
	# The legs alone: a body on the boards is a ceiling a jump hits.
	problems.append_array(MeshContract.check_collision_only(scene_root, COLLIDER_BODY))
	if problems.is_empty():
		var shapes: Array[Node] = scene_root.find_children("*", "CollisionShape3D", true, false)
		var solid: AABB = (shapes[0] as CollisionShape3D).shape.get_debug_mesh().get_aabb()
		var faces: AABB = face.get_aabb()
		if solid.end.y > faces.end.y:
			problems.append(
				(
					"the collider tops out at %.2f m, over the boards' %.2f m: it holds a board"
					% [solid.end.y, faces.end.y]
				)
			)
	return problems
