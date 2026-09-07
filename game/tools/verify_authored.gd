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
