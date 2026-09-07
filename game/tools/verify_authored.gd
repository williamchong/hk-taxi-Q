## Checks the authored door with a real DCC export (`P5-10`, `Q121`).
##
##     godot --headless --path game --script res://tools/verify_authored.gd
##
## The fixture is a Blender export — the Khronos exporter, not `gltf.py` — and
## the only asset in the repository that has come through a DCC tool. What it
## grades is the contract `ARCHITECTURE.md` states for a hand-made `.glb`:
## node names and hierarchy survive import, an unrecognised material keeps the
## PBR material the artist authored (its texture included), a `-col` node
## grows its collider and its sibling does not, and the landmark placement
## convention stands the model where the document says. Needs no built
## region, so `check.sh` runs it always.
extends SceneTree

const GeneratedLandmarks = preload("res://scripts/city/generated_landmarks.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")

const FIXTURE: String = "res://assets/authored/fixtures/dcc_roundtrip.glb"
## The vehicle door's fixture (`P5-23`): one Blender object, four material
## slots named from `generated_scene_import.gd`'s `VEHICLE` table, no vertex
## colours. Numbers below are `tools/make_dcc_fixture.py`'s `CAR_*` boxes in
## Godot's frame — Blender's y-forward is the exporter's -z.
const VEHICLE_FIXTURE: String = "res://assets/authored/fixtures/dcc_vehicle.glb"
const VEHICLE_MATERIAL: String = "res://tuning/vehicle_body.tres"
## Each box is 24 vertices under flat shading, and the four slots' payloads.
const VEHICLE_BOX_VERTICES: int = 24
const VEHICLE_PAYLOADS: Dictionary = {
	"paint": Vector2(0.0, 0.0),
	"glass": Vector2(0.0, 1.0),
	"brake": Vector2(1.0, 2.0),
	"headlamp": Vector2(6.0, 2.0),
}
## Where each box lies, in Godot's frame: `CAR_*`'s Blender (x, y, z) centre
## and size become (x, z, -y). A vertex on a shared plane — the cabin's base
## on the roof, a lens's face on the body's end — belongs to the smaller box,
## so those are asked first.
const VEHICLE_BOXES: Dictionary = {
	"brake": AABB(Vector3(0.45, 0.725, 2.0), Vector3(0.3, 0.15, 0.2)),
	"headlamp": AABB(Vector3(0.45, 0.725, -2.2), Vector3(0.3, 0.15, 0.2)),
	"glass": AABB(Vector3(-0.8, 1.1, -0.7), Vector3(1.6, 0.6, 1.8)),
	"paint": AABB(Vector3(-0.9, 0.2, -2.0), Vector3(1.8, 0.9, 4.0)),
}

## What `tools/make_dcc_fixture.py` authored, by name. The body carries `-col`
## in Blender; the importer strips the suffix and grows the collider.
const BODY: String = "KioskBody"
const ROOF: String = "KioskRoof"
const PAINT: String = "KioskPaint"
const ROOF_PAINT: String = "KioskRoofPaint"
## The packed colour grid, extracted beside the asset on first import.
const TEXTURE_PX: int = 64
## 12 on the cube and 10 on the six-sided cone: a count that moved means the
## importer welded, split or dropped something the artist drew.
const TRIANGLES: int = 22

## Where the placement test stands the kiosk. Nothing about the fixture is
## region-specific, so the numbers are arbitrary and the base is what is graded.
const STAND := Vector3(10.0, 2.0, 30.0)


func _init() -> void:
	var problems: PackedStringArray = []
	var packed := load(FIXTURE) as PackedScene
	if packed == null:
		printerr("  FAIL  %s did not load as a scene" % FIXTURE)
		quit(1)
		return
	var node: Node3D = packed.instantiate()

	# The importer strips the `-col` suffix, so the body is found by its bare name.
	var body := node.find_child(BODY, true, false) as MeshInstance3D
	var roof := node.find_child(ROOF, true, false) as MeshInstance3D
	problems.append_array(_check_hierarchy(body, roof))
	problems.append_array(_check_materials(body, roof))
	problems.append_array(_check_collision(node, roof))
	problems.append_array(_check_placement(node))
	var triangles: int = MeshContract.triangles(node)
	if triangles != TRIANGLES:
		problems.append("%d triangles imported, the fixture draws %d" % [triangles, TRIANGLES])
	node.free()
	problems.append_array(_check_vehicle_door())

	for problem: String in problems:
		printerr("  FAIL  ", problem)
	print("authored door: %s, %d problem(s)" % [FIXTURE, problems.size()])
	quit(1 if not problems.is_empty() else 0)


## The artist's names and parent-child structure are what the placement code
## and a scene editor address; an importer that flattened or renamed would
## leave every `find_child` in a placer looking for nothing.
func _check_hierarchy(body: MeshInstance3D, roof: MeshInstance3D) -> PackedStringArray:
	var problems: PackedStringArray = []
	if body == null:
		problems.append("no MeshInstance3D named %s — the -col suffix was not stripped?" % BODY)
	if roof == null:
		problems.append("no MeshInstance3D named %s" % ROOF)
	if body == null or roof == null:
		return problems
	if roof.get_parent() != body:
		problems.append("%s is not a child of %s — the hierarchy was flattened" % [ROOF, BODY])
	if roof.transform.origin.y <= 0.0:
		problems.append("%s lost its authored offset above the body" % ROOF)
	if roof.scale.is_equal_approx(Vector3.ONE):
		problems.append("%s lost its authored (unapplied) scale" % ROOF)
	return problems


## An unrecognised material name is left exactly as the artist authored it:
## the PBR material, its texture and its name all survive, and no shader is
## swapped in. A recognised name is `generated_scene_import.gd`'s table.
func _check_materials(body: MeshInstance3D, roof: MeshInstance3D) -> PackedStringArray:
	var problems: PackedStringArray = []
	if body == null or roof == null:
		return problems
	var paint := body.mesh.surface_get_material(0) as StandardMaterial3D
	if paint == null:
		problems.append("%s's material is not the StandardMaterial3D the artist authored" % BODY)
	else:
		if paint.resource_name != PAINT:
			problems.append(
				"%s's material is named %s, not %s" % [BODY, paint.resource_name, PAINT]
			)
		var albedo: Texture2D = paint.albedo_texture
		if albedo == null:
			problems.append("%s's albedo texture did not survive import" % PAINT)
		elif albedo.get_width() != TEXTURE_PX or albedo.get_height() != TEXTURE_PX:
			problems.append(
				(
					"%s's albedo texture is %dx%d, authored %dx%d"
					% [PAINT, albedo.get_width(), albedo.get_height(), TEXTURE_PX, TEXTURE_PX]
				)
			)
	var roof_paint := roof.mesh.surface_get_material(0) as StandardMaterial3D
	if roof_paint == null:
		problems.append("%s's material is not a StandardMaterial3D" % ROOF)
	elif roof_paint.resource_name != ROOF_PAINT:
		problems.append("%s's material is named %s" % [ROOF, roof_paint.resource_name])
	return problems


## `-col` on the body grows a trimesh collider there and nowhere else.
func _check_collision(node: Node3D, roof: MeshInstance3D) -> PackedStringArray:
	var problems: PackedStringArray = MeshContract.check_collision(node)
	if roof != null and MeshContract.has_collision(roof):
		problems.append("%s grew a collider without asking for one" % ROOF)
	return problems


## The landmark document's transform stands the model with its base at `pos`.
func _check_placement(node: Node3D) -> PackedStringArray:
	var entry: Dictionary = {
		"transform": {"pos": [STAND.x, STAND.y, STAND.z], "rot_y_deg": 90.0},
	}
	var placement: Variant = GeneratedLandmarks.placement_of(entry)
	if placement == null:
		return ["placement_of refused a well-formed transform"]
	var placed: AABB = (placement as Transform3D) * MeshContract.bounds(node)
	var problems: PackedStringArray = []
	if not is_equal_approx(placed.position.y, STAND.y):
		problems.append(
			"placed base at y=%.3f, the document says %.3f" % [placed.position.y, STAND.y]
		)
	if not placed.has_point(STAND + Vector3.UP):
		problems.append("placed model %s does not stand over %s" % [placed, STAND])
	return problems


## The vehicle door: four named slots in, one `vehicle_body` surface out, the
## payload on every vertex from the slot's name and a colour baked from the
## slot's base colour.
func _check_vehicle_door() -> PackedStringArray:
	var problems: PackedStringArray = []
	var packed := load(VEHICLE_FIXTURE) as PackedScene
	if packed == null:
		return ["%s did not load as a scene" % VEHICLE_FIXTURE]
	var node: Node3D = packed.instantiate()
	var mesh: ArrayMesh = MeshContract.single_primitive(node, 1, problems)
	if mesh == null or mesh.get_surface_count() != 1:
		node.free()
		return ["the vehicle fixture's body is not one surface — the door did not merge it"]
	problems.append_array(
		MeshContract.check_shader_material(mesh, 0, "the merged body", VEHICLE_MATERIAL)
	)
	var body := node.find_children("*", "MeshInstance3D", true, false)[0] as MeshInstance3D
	problems.append_array(_check_vehicle_payload(body))
	node.free()
	return problems


## How many per-vertex problems are spelled out before the rest are counted.
const FLAGGED: int = 4


## Classified by position, because after the merge the slot is gone and the
## position is the only thing that still says which box a vertex came from —
## in the node's frame, not the mesh's, because an export that kept a scale on
## the object carries unit-cube vertices under a scaled node.
func _check_vehicle_payload(body: MeshInstance3D) -> PackedStringArray:
	var problems: PackedStringArray = []
	var arrays: Array = body.mesh.surface_get_arrays(0)
	var payload: Variant = arrays[Mesh.ARRAY_TEX_UV]
	if typeof(payload) != TYPE_PACKED_VECTOR2_ARRAY:
		problems.append("the merged body carries no UV payload")
	if typeof(arrays[Mesh.ARRAY_COLOR]) != TYPE_PACKED_COLOR_ARRAY:
		problems.append("the merged body carries no COLOR_0 — the base colour was not baked")
	if not problems.is_empty():
		return problems
	var positions: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var uvs: PackedVector2Array = payload
	var counts: Dictionary = {}
	var wrong: int = 0
	for i: int in positions.size():
		var box: String = _vehicle_box_of(body.transform * positions[i])
		counts[box] = int(counts.get(box, 0)) + 1
		if not VEHICLE_PAYLOADS.has(box):
			wrong = _flag(
				problems, wrong, "vertex %d at %s lies in no fixture box" % [i, positions[i]]
			)
		elif uvs[i] != VEHICLE_PAYLOADS[box]:
			wrong = _flag(
				problems,
				wrong,
				(
					"vertex %d in the %s box carries %s, the door should stamp %s"
					% [i, box, uvs[i], VEHICLE_PAYLOADS[box]]
				)
			)
	if wrong > FLAGGED:
		problems.append("%d vertices in all carry the wrong payload" % wrong)
	for box: String in VEHICLE_PAYLOADS:
		if int(counts.get(box, 0)) != VEHICLE_BOX_VERTICES:
			problems.append(
				(
					"%d vertices in the %s box, the fixture draws %d"
					% [counts.get(box, 0), box, VEHICLE_BOX_VERTICES]
				)
			)
	return problems


## Append `message` while under the cap; returns the running count either way.
static func _flag(problems: PackedStringArray, so_far: int, message: String) -> int:
	if so_far < FLAGGED:
		problems.append(message)
	return so_far + 1


## The box a vertex belongs to, smallest first, grown a millimetre so a corner
## on the box's own face counts as inside it.
static func _vehicle_box_of(position: Vector3) -> String:
	for box: String in VEHICLE_BOXES:
		var extent: AABB = VEHICLE_BOXES[box]
		if extent.grow(0.001).has_point(position):
			return box
	return "outside"
