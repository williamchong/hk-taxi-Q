## Checks generated city tiles against the data contract, headless.
##
## `P1-2` accepts a tile only if it loads in Godot, costs under three draw calls,
## carries vertex colours, and references no texture. Those are engine-side
## facts, so the ETL cannot assert them and a human eyeballing the editor will
## not catch a regression. Run:
##
##     godot --headless --path game --script res://tools/verify_tiles.gd
##
## Exits non-zero on the first tile that fails.
extends SceneTree

const GeneratedTiles = preload("res://scripts/city/generated_tiles.gd")

## Draw calls per tile. `P1-2` accepts "under three", so three is a failure.
const MAX_SURFACES: int = 2


func _init() -> void:
	var failures: int = 0
	var checked: int = 0

	for file: String in GeneratedTiles.files():
		checked += 1
		var problems: PackedStringArray = _check(file)
		if problems.is_empty():
			print("  ok    ", file.get_file())
		else:
			failures += 1
			for problem: String in problems:
				printerr("  FAIL  ", file.get_file(), ": ", problem)

	if checked == 0:
		printerr(GeneratedTiles.missing_hint())
		quit(1)
		return

	print("%d tiles checked, %d failed" % [checked, failures])
	quit(1 if failures > 0 else 0)


func _check(path: String) -> PackedStringArray:
	var problems: PackedStringArray = []

	var packed: PackedScene = GeneratedTiles.load_tile(path)
	if packed == null:
		problems.append("did not load as a scene")
		return problems

	var root: Node = packed.instantiate()
	var instances: Array[Node] = root.find_children("*", "MeshInstance3D", true, false)
	if instances.is_empty():
		problems.append("contains no MeshInstance3D")

	var surfaces: int = 0
	for instance: MeshInstance3D in instances:
		var mesh: Mesh = instance.mesh
		if mesh == null:
			problems.append("%s has no mesh" % instance.name)
			continue
		surfaces += mesh.get_surface_count()
		for surface: int in mesh.get_surface_count():
			problems.append_array(_check_surface(mesh, surface, instance.name))

	# One draw call per surface. The budget is stated in draw calls because that
	# is what the mobile tier runs out of first.
	if surfaces > MAX_SURFACES:
		problems.append("%d surfaces, over the %d-surface budget" % [surfaces, MAX_SURFACES])

	root.free()
	return problems


func _check_surface(mesh: Mesh, surface: int, owner_name: String) -> PackedStringArray:
	# Surface indices restart per MeshInstance3D, so the owner's name is what
	# makes "surface 0" unambiguous once a tile holds more than one.
	var where: String = "%s surface %d" % [owner_name, surface]
	var problems: PackedStringArray = []

	if not (mesh.surface_get_format(surface) & Mesh.ARRAY_FORMAT_COLOR):
		problems.append("%s carries no vertex colours" % where)

	var material: BaseMaterial3D = mesh.surface_get_material(surface) as BaseMaterial3D
	if material == null:
		problems.append("%s has no BaseMaterial3D" % where)
		return problems

	if not material.vertex_color_use_as_albedo:
		problems.append("%s ignores its vertex colours" % where)
	for slot: int in [
		BaseMaterial3D.TEXTURE_ALBEDO,
		BaseMaterial3D.TEXTURE_NORMAL,
		BaseMaterial3D.TEXTURE_ORM,
	]:
		if material.get_texture(slot) != null:
			problems.append("%s references a texture in slot %d" % [where, slot])
	return problems
