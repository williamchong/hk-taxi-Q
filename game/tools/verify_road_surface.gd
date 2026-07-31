## Checks the generated road surface against the data contract, headless.
##
## `P1-4` delivers a drivable surface with collision. Whether Godot's importer
## actually built that collider from the `-col` suffix in the mesh name is an
## engine-side fact, so the ETL cannot assert it and its own tests cannot see
## it — the same gap `verify_tiles.gd` exists to close. Run:
##
##     godot --headless --path game --script res://tools/verify_road_surface.gd
##
## Exits non-zero if the surface is missing or fails any check.
extends SceneTree

const GeneratedRoadSurface = preload("res://scripts/city/generated_road_surface.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")

## One primitive, so the whole region's roads cost one draw call — the same
## rule the tiles are held to, and the reason the surface is untextured.
const SURFACES: int = 1


func _init() -> void:
	var packed: PackedScene = GeneratedRoadSurface.load_surface()
	if packed == null:
		printerr(GeneratedRoadSurface.missing_hint())
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
		print("  ok    ", GeneratedRoadSurface.PATH)
	quit(1 if not problems.is_empty() else 0)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []

	var instances: Array[Node] = scene_root.find_children("*", "MeshInstance3D", true, false)
	if instances.size() != 1:
		problems.append("expected one MeshInstance3D, found %d" % instances.size())
		return problems

	var mesh := (instances[0] as MeshInstance3D).mesh as ArrayMesh
	if mesh == null:
		problems.append("the MeshInstance3D carries no ArrayMesh")
		return problems
	# Exactly, not at most: a mesh with no surfaces at all would otherwise pass
	# every check below by never entering the loop.
	if mesh.get_surface_count() != SURFACES:
		problems.append("%d surfaces, expected %d" % [mesh.get_surface_count(), SURFACES])

	for surface: int in mesh.get_surface_count():
		problems.append_array(MeshContract.check_surface(mesh, surface, "surface %d" % surface))
		# The only rule the road surface adds to the shared contract. The
		# markings shader in `docs/ART_DESIGN.md` is driven by these: U is a
		# lane coordinate, V is metres along the carriageway.
		if not (mesh.surface_get_format(surface) & Mesh.ARRAY_FORMAT_TEX_UV):
			problems.append("surface %d carries no UVs" % surface)

	# The `-col` suffix should have left a static body with trimesh collision
	# beside the mesh, and taken the suffix off the node name on the way.
	var bodies: Array[Node] = scene_root.find_children("*", "StaticBody3D", true, false)
	if bodies.is_empty():
		problems.append("no StaticBody3D — the `-col` name suffix did not import as collision")
	else:
		var shapes: Array[Node] = bodies[0].find_children("*", "CollisionShape3D", true, false)
		if shapes.is_empty():
			problems.append("the StaticBody3D has no CollisionShape3D")
		elif ((shapes[0] as CollisionShape3D).shape as ConcavePolygonShape3D) == null:
			problems.append("collision is not a ConcavePolygonShape3D")

	return problems
