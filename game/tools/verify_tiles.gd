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

const Manifest = preload("res://scripts/city/city_manifest.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")

## Draw calls per tile. `P1-2` accepts "under three", so three is a failure.
const MAX_SURFACES: int = 2


func _init() -> void:
	# The manifest rather than a directory listing, so this checks the shipped
	# set by construction — a file the build no longer names stops being checked
	# instead of failing a check nobody will act on.
	#
	# `load_manifest` has already pushed the reason, which for a stale schema is
	# not the missing-file hint; repeating one here would name the wrong fix.
	var manifest: Manifest = Manifest.load_manifest()
	if manifest == null:
		quit(1)
		return

	var failures: int = 0
	var checked: int = 0

	for tile: Manifest.Tile in manifest.tiles:
		for file: String in tile.lods:
			checked += 1
			var problems: PackedStringArray = _check(file)
			if problems.is_empty():
				print("  ok    ", file.get_file())
			else:
				failures += 1
				for problem: String in problems:
					printerr("  FAIL  ", file.get_file(), ": ", problem)

	if checked == 0:
		printerr("  FAIL  %s names no tiles" % Manifest.PATH)
		quit(1)
		return

	print("%d tiles checked, %d failed" % [checked, failures])
	quit(1 if failures > 0 else 0)


func _check(path: String) -> PackedStringArray:
	var problems: PackedStringArray = []

	var packed := load(path) as PackedScene
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
			# Surface indices restart per MeshInstance3D, so the owner's name is
			# what makes "surface 0" unambiguous once a tile holds more than one.
			problems.append_array(
				MeshContract.check_surface(
					mesh, surface, "%s surface %d" % [instance.name, surface]
				)
			)

	# One draw call per surface. The budget is stated in draw calls because that
	# is what the mobile tier runs out of first.
	if surfaces > MAX_SURFACES:
		problems.append("%d surfaces, over the %d-surface budget" % [surfaces, MAX_SURFACES])

	root.free()
	return problems
