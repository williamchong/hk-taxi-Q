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

const BuildingIndex = preload("res://scripts/city/building_index.gd")
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

## What the ETL names the tile collider's node, less its `-colonly` suffix
## (`P5-12`): `COLLIDER_NAME_SUFFIX` in `etl/pipeline/buildings.py`. The
## importer strips the suffix and keeps the rest as the `StaticBody3D`'s name.
const COLLIDER_BODY_SUFFIX: String = "_collision"

## The surface markers `TEXCOORD_1.x` may carry, mirroring `SurfaceClass` in
## `etl/pipeline/config.py`: 0 facade, 1 ground, 2 structure.
const MARKER_MAX: int = 2

## The decimation slack every vertex is held to, the picker's own.
const ROW_SLACK_M: float = BuildingIndex.ROW_SLACK_M

## How many rows per tier the picker is asked to resolve from their own box
## centre. Every row is checked vertex by vertex; this is the end-to-end walk
## through `BuildingIndex.object_at`, on a sample.
const PICKS_PER_TIER: int = 3


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
			var problems: PackedStringArray = _check(file, tier, tile)
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


func _check(path: String, tier: int, tile: Manifest.Tile) -> PackedStringArray:
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
			problems.append_array(_check_identity(instance, mesh, surface, where))

	# One draw call per surface. The budget is stated in draw calls because that
	# is what the mobile tier runs out of first.
	if surfaces > MAX_SURFACES:
		problems.append("%d surfaces, over the %d-surface budget" % [surfaces, MAX_SURFACES])

	problems.append_array(_check_collision(scene_root, tier, tile.id))
	problems.append_array(_check_occluder(scene_root, tier, tile))
	# Static Lightmaps would regenerate UV2 over the identity payload (`P5-11`),
	# and catching it at the import setting names the fix, where the mesh check
	# only names the symptom.
	problems.append_array(
		MeshContract.check_uv2_import_settings(path, "identity payload in TEXCOORD_1")
	)

	scene_root.free()
	return problems


## The window-band shader reached the tile, and has something to read (`P3-7`).
##
## Both halves are silent failures, which is the only reason they are worth a
## check. `TEXCOORD_0` is the planar façade UV — metres along and metres above
## the object's own base — and `TEXCOORD_1` the marker, phase and object row
## (`P5-11`): the things a shader cannot derive from a vertex. The material is
## how the shader arrives at all. Lose any and the tile renders in flat vertex
## colour, which is precisely what the city looked like *before* `P3-7`: no
## error, no missing file, nothing on screen that reads as broken.
##
## Every tier is checked, not just the finest. The payload is a property of the
## geometry, and which tiers actually draw bands is the shader's distance fade to
## decide rather than the exporter's.
func _check_facade_payload(mesh: Mesh, surface: int, where: String) -> PackedStringArray:
	var problems: PackedStringArray = []

	var format: int = mesh.surface_get_format(surface)
	if not (format & Mesh.ARRAY_FORMAT_TEX_UV):
		problems.append("%s carries no TEXCOORD_0; the window shader has nothing to read" % where)
	if not (format & Mesh.ARRAY_FORMAT_TEX_UV2):
		problems.append("%s carries no TEXCOORD_1; the marker and object row are missing" % where)

	problems.append_array(MeshContract.check_shader_material(mesh, surface, where, FACADE_MATERIAL))
	return problems


## The identity channel and its table agree (`P5-11`).
##
## Three things, each a silent failure on its own: the table arrived (an
## importer that dropped `extras` leaves a tile nobody can pick a building in,
## rendering perfectly); every vertex names a row that exists and a marker the
## shader knows; and every vertex stands inside the box its row claims, within
## `ROW_SLACK_M` — a vertex far outside is a row index that survived a
## `collapse` it should not have, or a table cut from the wrong ordinals. Then
## the end-to-end walk on a sample: `BuildingIndex.object_at` asked for the
## centre of a row's own box returns that row, or a smaller box nested in it.
##
## ⚠️ This is also the tripwire for a lightmap unwrap (`meshes/light_baking =
## 2`) or a stale `.import` rewriting UV2: an unwrap writes fractions in
## `[0, 1]`, which fail the row check on every vertex of every object but the
## first.
func _check_identity(
	instance: MeshInstance3D, mesh: Mesh, surface: int, where: String
) -> PackedStringArray:
	var problems: PackedStringArray = []
	var rows: Array = BuildingIndex.objects_of(mesh)
	if rows.is_empty():
		problems.append("%s brought no object table (mesh extras)" % where)
		return problems
	if not (mesh.surface_get_format(surface) & Mesh.ARRAY_FORMAT_TEX_UV2):
		return problems

	var arrays: Array = mesh.surface_get_arrays(surface)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var uv2: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV2]
	var boxes: Array[AABB] = []
	for row: Dictionary in rows:
		var box: Variant = BuildingIndex.box_of(row)
		if box == null:
			problems.append("%s: row %s has no usable aabb" % [where, row.get("id")])
			return problems
		boxes.append((box as AABB).grow(ROW_SLACK_M))

	var bad_row: int = 0
	var bad_marker: int = 0
	var outside: int = 0
	# The first vertex each row owns, `-1` where it owns none in this tier —
	# recorded on this walk so the picker probe below needs no second one.
	var first_vertex_of_row: PackedInt32Array = PackedInt32Array()
	first_vertex_of_row.resize(rows.size())
	first_vertex_of_row.fill(-1)
	for i: int in vertices.size():
		var index: int = BuildingIndex.row_of(uv2[i])
		if index < 0 or index >= rows.size() or absf(uv2[i].y - float(index)) > 1e-4:
			bad_row += 1
			continue
		if first_vertex_of_row[index] < 0:
			first_vertex_of_row[index] = i
		var marker: int = int(floor(uv2[i].x))
		if marker < 0 or marker > MARKER_MAX:
			bad_marker += 1
		if not boxes[index].has_point(vertices[i]):
			outside += 1
	if bad_row > 0:
		problems.append(
			"%s: %d vertices name no row of the %d-row table" % [where, bad_row, rows.size()]
		)
	if bad_marker > 0:
		problems.append("%s: %d vertices carry a marker above %d" % [where, bad_marker, MARKER_MAX])
	if outside > 0:
		problems.append(
			(
				"%s: %d vertices stand over %.0f m outside their row's box"
				% [where, outside, ROW_SLACK_M]
			)
		)

	# The picker, end to end, on a sample of rows spread through the table:
	# asked at a vertex the row itself owns — where a raycast hit would land —
	# it must answer that row, whatever neighbouring boxes overlap it.
	# `floori` of a float divide rather than an integer one: GDScript warns on
	# integer division and `check.sh` promotes warnings to errors.
	var step: int = maxi(1, floori(rows.size() / float(PICKS_PER_TIER)))
	for k: int in range(0, rows.size(), step):
		var row: Dictionary = rows[k]
		var probe: int = first_vertex_of_row[k]
		if probe < 0:
			problems.append("%s: row %s owns no vertex in this tier" % [where, row.get("id")])
			continue
		var found: Dictionary = BuildingIndex.object_at(instance, vertices[probe])
		if found != row and not _shares_vertex(found, rows, vertices, uv2, vertices[probe]):
			problems.append(
				(
					"%s: object_at at a vertex of %s answered %s"
					% [where, row.get("id"), found.get("id", "nothing")]
				)
			)
	return problems


## Whether `other` owns a vertex at exactly `at` — two buildings sharing a wall
## corner tie at distance zero, and which the picker answers is not a defect.
func _shares_vertex(
	other: Dictionary,
	rows: Array,
	vertices: PackedVector3Array,
	uv2: PackedVector2Array,
	at: Vector3
) -> bool:
	var index: int = rows.find(other)
	if index < 0:
		return false
	for i: int in vertices.size():
		if BuildingIndex.row_of(uv2[i]) == index and vertices[i] == at:
			return true
	return false


## The occluder is a `-occonly` node beside exactly the tiers the manifest
## says the ETL built one for (`P5-13`, per tier since `P5-17`) — and nowhere
## it says it did not, which is what makes a dropped occluder a failure rather
## than a tile that happens to occlude nothing, and an occluder in a tier the
## policy left bare a failure rather than a free win. ⚠️ Unlike the collider
## it cannot be asserted by name: the importer names every one
## `OccluderInstance3D`.
func _check_occluder(scene_root: Node, tier: int, tile: Manifest.Tile) -> PackedStringArray:
	if tile.occluder.size() != tile.lods.size():
		return PackedStringArray(
			[
				(
					"the manifest names %d occluder flags for %d tiers"
					% [tile.occluder.size(), tile.lods.size()]
				)
			]
		)
	if tile.has_occluder(tier):
		return MeshContract.check_occluder_only(scene_root)
	return MeshContract.check_no_occluder(scene_root, "%s tier %d" % [tile.id, tier])


## Collision is a `-colonly` body beside the finest tier, named for the tile,
## and absent everywhere else (`P5-12`).
##
## The shape of the collider is `MeshContract`'s to judge; the tier it belongs
## to is this tool's, because only the manifest knows how many tiers a tile has.
func _check_collision(scene_root: Node, tier: int, tile_id: String) -> PackedStringArray:
	if tier == COLLISION_TIER:
		return MeshContract.check_collision_only(scene_root, tile_id + COLLIDER_BODY_SUFFIX)

	if MeshContract.has_collision(scene_root):
		return PackedStringArray(
			[
				(
					(
						"LOD%d carries collision; only LOD%d should. A collider has "
						+ "spread to a tier nothing can touch."
					)
					% [tier, COLLISION_TIER]
				)
			]
		)
	return PackedStringArray()
