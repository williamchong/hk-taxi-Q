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
			problems.append_array(_check_survey_payload(mesh, surface, where))

	# One draw call per surface. The budget is stated in draw calls because that
	# is what the mobile tier runs out of first.
	if surfaces > MAX_SURFACES:
		problems.append("%d surfaces, over the %d-surface budget" % [surfaces, MAX_SURFACES])

	problems.append_array(_check_collision(scene_root, tier))
	problems.append_array(_check_import_settings(path))

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

	var material := mesh.surface_get_material(surface) as ShaderMaterial
	if material == null:
		problems.append(
			(
				(
					"%s did not import with a ShaderMaterial; the ETL's `city_facade` material "
					+ "name and `tools/generated_scene_import.gd` have stopped agreeing"
				)
				% where
			)
		)
	elif material.resource_path != FACADE_MATERIAL:
		problems.append("%s uses %s, not %s" % [where, material.resource_path, FACADE_MATERIAL])
	return problems


## The survey payload holds the codec's invariants (schema 6, `Q40`/`Q41`).
##
## `TEXCOORD_1.x` must be a small exact integer whose decoded fields are in
## range, and `y` must still be unwritten. Beyond the contract itself this is
## the tripwire for both import hazards: a lightmap unwrap
## (`meshes/light_baking = 2`) replaces the channel with fractions in [0, 1],
## and 16-bit attribute compression corrupts large codes — either way the
## exactness or range checks fail. A full scan rather than a sample, because
## this is the offline verify tool and one wrong vertex is a wrong building.
func _check_survey_payload(mesh: Mesh, surface: int, where: String) -> PackedStringArray:
	if not (mesh.surface_get_format(surface) & Mesh.ARRAY_FORMAT_TEX_UV2):
		return PackedStringArray(
			["%s carries no TEXCOORD_1; the survey payload is missing" % where]
		)

	var uv2s: PackedVector2Array = mesh.surface_get_arrays(surface)[Mesh.ARRAY_TEX_UV2]
	for uv2: Vector2 in uv2s:
		var code: float = uv2.x
		var glazed: float = fmod(code, 4.0)
		var tint: float = fmod(floor(code / 4.0), 256.0)
		var grammar: float = floor(code / 1024.0)
		if (
			uv2.y != 0.0
			or code != floor(code)
			or code < 0.0
			or code >= 8192.0
			or glazed > 2.0
			or tint > 240.0
			or grammar > 5.0
		):
			return PackedStringArray(
				[
					(
						(
							"%s: TEXCOORD_1 (%f, %f) breaks the survey codec — the ETL and "
							+ "shader disagree, or the importer rewrote the channel "
							+ "(lightmap unwrap or attribute compression)"
						)
						% [where, uv2.x, uv2.y]
					)
				]
			)
	return PackedStringArray()


## The importer settings that would destroy the payload have not drifted.
##
## `meshes/light_baking = 2` (Static Lightmaps) makes the importer generate its
## own UV2 unwrap, silently overwriting the survey payload with texture
## coordinates that pass every visual inspection — `docs/ART_DESIGN.md` records
## the hazard. 1 is Static, which leaves the channel alone.
func _check_import_settings(path: String) -> PackedStringArray:
	var import_path: String = path + ".import"
	var file := FileAccess.open(import_path, FileAccess.READ)
	if file == null:
		return PackedStringArray(["%s has no .import beside it" % path])
	if not file.get_as_text().contains("meshes/light_baking=1"):
		return PackedStringArray(
			[
				(
					(
						"%s: meshes/light_baking is not 1 (Static). Static Lightmaps "
						+ "regenerates UV2 and overwrites the survey payload."
					)
					% import_path
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
