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

## The material a tile must end up with, mirroring `SHADERS` in
## `tools/generated_scene_import.gd` and `FACADE_MATERIAL` in
## `etl/pipeline/buildings.py`.
##
## Checked because the dispatch that produces it has **no failing state**: if the
## ETL stopped naming the material, or the import script stopped recognising the
## name, every tile would quietly keep its default `BaseMaterial3D`, pass every
## other check here, and render in flat vertex colour — which is exactly what the
## city looked like before `P3-7`. There is nothing to see and nothing to catch.
const FACADE_MATERIAL: String = "res://tuning/city_facade.tres"


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
			var where: String = "%s surface %d" % [instance.name, surface]
			problems.append_array(MeshContract.check_surface(mesh, surface, where))
			problems.append_array(_check_facade_payload(mesh, surface, where))
			problems.append_array(_check_no_survey_channel(mesh, surface, where))

	# One draw call per surface. The budget is stated in draw calls because that
	# is what the mobile tier runs out of first.
	if surfaces > MAX_SURFACES:
		problems.append("%d surfaces, over the %d-surface budget" % [surfaces, MAX_SURFACES])

	problems.append_array(_check_collision(scene_root, tier))
	# Still pinned with no payload left to protect (`Q102`): Static Lightmaps
	# would *create* the UV2 `_check_no_survey_channel` now requires to be
	# absent, and catching it at the import setting names the fix, where the
	# mesh check only names the symptom. ⚠️ The shared helper's sentence is an
	# *overwrite* framing, so the noun has to be the empty slot rather than a
	# payload — there is no payload here to overwrite.
	problems.append_array(
		MeshContract.check_uv2_import_settings(path, "UV2 slot the tiles must keep empty")
	)

	scene_root.free()
	return problems


## The window-band shader reached the tile, and has something to read (`P3-7`).
##
## Both halves are silent failures, which is the only reason they are worth a
## check. `TEXCOORD_0` is height above the object's own base and a surface
## marker — the two things a shader cannot derive from a vertex — and the
## material is how the shader arrives at all. Lose either and the tile renders in
## flat vertex colour, which is precisely what the city looked like *before*
## `P3-7`: no error, no missing file, nothing on screen that reads as broken.
##
## Every tier is checked, not just the finest. The payload is a property of the
## geometry, and which tiers actually draw bands is the shader's distance fade to
## decide rather than the exporter's.
func _check_facade_payload(mesh: Mesh, surface: int, where: String) -> PackedStringArray:
	var problems: PackedStringArray = []

	if not (mesh.surface_get_format(surface) & Mesh.ARRAY_FORMAT_TEX_UV):
		problems.append("%s carries no TEXCOORD_0; the window shader has nothing to read" % where)

	problems.append_array(MeshContract.check_shader_material(mesh, surface, where, FACADE_MATERIAL))
	return problems


## No tile carries a TEXCOORD_1 at all (schema 20, `Q102`).
##
## ⚠️ **This check was inverted rather than deleted, and it still catches the
## hazard it was written for.** Until `Q102` it decoded a packed facade-survey
## payload here and held every vertex to the codec's field ceilings, which made
## it the tripwire for a lightmap unwrap (`meshes/light_baking = 2`) or 16-bit
## attribute compression rewriting the channel. The vision reader that filled
## the payload was withdrawn on cost, so the ETL ships no UV2 — and a lightmap
## unwrap *writes* UV2, so the presence of the channel is now the whole signal.
## Cheaper and stricter than the codec scan it replaces: it needs no vertex
## walk, and there is no legal value to be confused with a corrupted one.
func _check_no_survey_channel(mesh: Mesh, surface: int, where: String) -> PackedStringArray:
	if mesh.surface_get_format(surface) & Mesh.ARRAY_FORMAT_TEX_UV2:
		return PackedStringArray(
			[
				(
					(
						"%s carries a TEXCOORD_1; the ETL ships none since schema 20, so "
						+ "the importer wrote it (lightmap unwrap or a stale .import "
						+ "sidecar) or the bundle predates the survey's withdrawal"
					)
					% where
				)
			]
		)
	return PackedStringArray()


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
