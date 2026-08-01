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

## The one tier that ships a collider, mirroring `COLLISION_TIER` in
## `etl/pipeline/buildings.py`.
##
## Checked in both directions, and the absent-on-coarse-tiers half is the one
## worth having: a `-col` suffix that spread is invisible in every screenshot and
## shows up only as bundle bytes, which is `Q16`'s failure mode exactly.
const COLLISION_TIER: int = 0


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
		for tier: int in tile.lods.size():
			var file: String = tile.lods[tier]
			checked += 1
			var problems: PackedStringArray = _check(file, tier)
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


func _check(path: String, tier: int) -> PackedStringArray:
	var problems: PackedStringArray = []

	var packed := load(path) as PackedScene
	if packed == null:
		problems.append("did not load as a scene")
		return problems

	var scene_root: Node = packed.instantiate()
	var instances: Array[Node] = scene_root.find_children("*", "MeshInstance3D", true, false)
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

	problems.append_array(_check_collision(scene_root, tier))

	scene_root.free()
	return problems


## Collision is present on the finest tier and absent everywhere else.
##
## The shape of the collider is `MeshContract`'s to judge; the tier it belongs
## to is this tool's, because only the manifest knows how many tiers a tile has.
func _check_collision(scene_root: Node, tier: int) -> PackedStringArray:
	if tier == COLLISION_TIER:
		return MeshContract.check_collision(scene_root)

	if MeshContract.has_collision(scene_root):
		return PackedStringArray(
			[
				(
					(
						"LOD%d carries collision; only LOD%d should. A `-col` suffix has "
						+ "spread to a tier nothing can touch."
					)
					% [tier, COLLISION_TIER]
				)
			]
		)
	return PackedStringArray()
