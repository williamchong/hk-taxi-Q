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

const TILE_DIR: String = "res://assets/generated/tiles"
const MAX_SURFACES: int = 2


func _init() -> void:
	var failures: int = 0
	var checked: int = 0

	for file: String in _tile_files():
		checked += 1
		var problems: PackedStringArray = _check(file)
		if problems.is_empty():
			print("  ok    ", file.get_file())
		else:
			failures += 1
			for problem: String in problems:
				printerr("  FAIL  ", file.get_file(), ": ", problem)

	if checked == 0:
		printerr("no tiles under ", TILE_DIR, " — copy the ETL output there first")
		quit(1)
		return

	print("%d tiles checked, %d failed" % [checked, failures])
	quit(1 if failures > 0 else 0)


func _tile_files() -> PackedStringArray:
	var files: PackedStringArray = []
	for name: String in DirAccess.get_files_at(TILE_DIR):
		# Godot reports the imported `.glb` under its source name in the editor
		# but as `.glb` on disk; either way the import is what `load` returns.
		if name.ends_with(".glb"):
			files.append(TILE_DIR.path_join(name))
	files.sort()
	return files


func _check(path: String) -> PackedStringArray:
	var problems: PackedStringArray = []

	var packed: PackedScene = load(path) as PackedScene
	if packed == null:
		problems.append("did not load as a scene")
		return problems

	var root: Node = packed.instantiate()
	var instances: Array[MeshInstance3D] = []
	_collect(root, instances)

	if instances.is_empty():
		problems.append("contains no MeshInstance3D")

	var surfaces: int = 0
	for instance: MeshInstance3D in instances:
		var mesh: Mesh = instance.mesh
		surfaces += mesh.get_surface_count()

		for surface: int in mesh.get_surface_count():
			if not (mesh.surface_get_format(surface) & Mesh.ARRAY_FORMAT_COLOR):
				problems.append("surface %d carries no vertex colours" % surface)

			var material: BaseMaterial3D = mesh.surface_get_material(surface) as BaseMaterial3D
			if material == null:
				problems.append("surface %d has no BaseMaterial3D" % surface)
				continue
			if not material.vertex_color_use_as_albedo:
				problems.append("surface %d ignores its vertex colours" % surface)
			for slot: int in [
				BaseMaterial3D.TEXTURE_ALBEDO,
				BaseMaterial3D.TEXTURE_NORMAL,
				BaseMaterial3D.TEXTURE_ORM,
			]:
				if material.get_texture(slot) != null:
					problems.append("surface %d references a texture in slot %d" % [surface, slot])

	# One draw call per surface. The budget is stated in draw calls because that
	# is what the mobile tier runs out of first.
	if surfaces > MAX_SURFACES:
		problems.append("%d surfaces, over the %d-surface budget" % [surfaces, MAX_SURFACES])

	root.free()
	return problems


func _collect(node: Node, into: Array[MeshInstance3D]) -> void:
	if node is MeshInstance3D and (node as MeshInstance3D).mesh != null:
		into.append(node as MeshInstance3D)
	for child: Node in node.get_children():
		_collect(child, into)
