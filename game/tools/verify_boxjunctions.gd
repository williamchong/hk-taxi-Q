## Checks the generated yellow box junctions against the data contract, headless.
##
## `P3-18` delivers TD's published box polygons as geometry rather than as paint
## on the ribbon, and the facts that decision rests on are engine-side: whether
## the importer dispatched the shader on the material name, whether it built a
## collider it must *not* have, and — the one that matters most — whether every
## triangle still faces the sky. Run:
##
##     godot --headless --path game --script res://tools/verify_boxjunctions.gd
##
## Exits non-zero if the boxes are present and fail any check.
##
## ⚠️ **Absence is a pass, and that is not a loophole** — `verify_arrows.gd`'s
## paragraph, unchanged: a city whose estate publishes no box polygons ships
## none and `city.json` names null. What stops that becoming a silent skip is
## `verify_city.gd`, whose `_check_documents` asserts a *named* box-junction
## asset exists and matches this file's constant.
extends SceneTree

const GeneratedBoxJunctions = preload("res://scripts/city/generated_boxjunctions.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")

## One primitive, so the whole region's boxes cost one draw call — the rule the
## road surface, the tiles, the tramway and the arrows are all held to.
const SURFACES: int = 1

## The material the boxes must end up with, mirroring `SHADERS` in
## `tools/generated_scene_import.gd` and `BOXJUNCTIONS_MATERIAL` in
## `etl/pipeline/boxjunctions.py`.
##
## Checked because the dispatch has **no failing state**: boxes that kept their
## imported `BaseMaterial3D` would be the right hatching on the right junctions
## in whatever colour the importer chose, and nothing else here would notice.
const BOXJUNCTIONS_MATERIAL: String = "res://tuning/boxjunctions.tres"

## How far a triangle may tilt off horizontal before it is a fold rather than a
## slope. The hatch takes the junction's grade per vertex, and the steepest
## street in the region is well inside this; what it catches is a triangle at or
## past vertical, which is a winding failure.
const MIN_FACING_UP: float = 0.1


func _init() -> void:
	if not GeneratedBoxJunctions.is_present():
		print("  skip  no box junctions shipped for this region")
		quit(0)
		return

	var packed: PackedScene = GeneratedBoxJunctions.load_boxjunctions()
	if packed == null:
		# Present but unloadable, which is not the same as absent — the hint
		# about rebuilding would be the wrong advice here.
		printerr("  FAIL  %s exists but did not load as a scene" % GeneratedBoxJunctions.PATH)
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
		print("  ok    ", GeneratedBoxJunctions.PATH)
	quit(1 if not problems.is_empty() else 0)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []

	var mesh: ArrayMesh = MeshContract.single_primitive(scene_root, SURFACES, problems)
	if mesh == null:
		return problems

	for surface: int in mesh.get_surface_count():
		var where: String = "surface %d" % surface
		# `false`: this mesh ships no `COLOR_0` on purpose — see
		# `BOXJUNCTIONS_MATERIAL` above and `config.BoxJunctions`. Every other
		# guarantee in `check_surface` still applies, the no-texture one
		# especially.
		problems.append_array(MeshContract.check_surface(mesh, surface, where, false))
		problems.append_array(
			MeshContract.check_shader_material(mesh, surface, where, BOXJUNCTIONS_MATERIAL)
		)
		problems.append_array(_check_faces_up(mesh, surface, where))

	problems.append_array(_check_has_no_collision(scene_root))
	return problems


## Paint must **not** collide, for the reason the arrows must not.
##
## Sharper again here: the hatch crosses the middle of every boxed junction, so
## a collider would be a 12 mm step every vehicle in the region crosses at speed
## while turning — and the whole guard against it is the absence of a `-col`
## suffix in one string in `boxjunctions.py`.
func _check_has_no_collision(scene_root: Node3D) -> PackedStringArray:
	return MeshContract.check_no_collision(
		scene_root, "the box junctions", "BOXJUNCTIONS_MESH_NAME in etl/pipeline/boxjunctions.py"
	)


## Every triangle faces the sky (`P3-18`).
##
## ⚠️ **This asset's version of the failure that fails to nothing.**
## `boxjunctions.gdshader` is `cull_back`, so winding decides visibility and the
## normal attribute does not: a mesh wound the other way is correct geometry, in
## the correct place, with the correct material, and the city simply has no box
## junctions in it. The tramway shipped exactly that — **5,111 of 5,112**
## triangles facing the ground — and no frame showed it.
##
## Checked here as well as in `boxjunctions.json` because the two catch
## different things. The ETL's `inverted` counts what `pipeline/boxjunctions.py`
## built; this counts what Godot imported, and an import that mirrors an axis
## moves one without the other.
func _check_faces_up(mesh: Mesh, surface: int, where: String) -> PackedStringArray:
	var arrays: Array = mesh.surface_get_arrays(surface)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	if indices.is_empty():
		return PackedStringArray(["%s carries no index buffer to check winding on" % where])

	var inverted: int = 0
	# `floori` of a float divide rather than an integer one: GDScript warns on
	# integer division and `check.sh` promotes warnings to errors, so the plain
	# form does not compile. The count is exact — an index buffer is always a
	# multiple of three.
	var triangles: int = floori(indices.size() / 3.0)
	for triangle: int in triangles:
		var a: Vector3 = vertices[indices[triangle * 3]]
		var b: Vector3 = vertices[indices[triangle * 3 + 1]]
		var c: Vector3 = vertices[indices[triangle * 3 + 2]]
		# ⚠️ **Negated, because Godot winds front faces clockwise and glTF winds
		# them counter-clockwise** — `verify_arrows.gd`'s expression, kept
		# verbatim. The sign was established by measurement against `roads.glb`
		# (32,222 of 32,233 down here) and `tram.glb` (5,132 of 5,132); if this
		# ever needs revisiting, re-measure against those two rather than
		# re-reading this comment, and do not "fix" either side to agree with
		# the other (`Q59`).
		var cross: Vector3 = (a - b).cross(c - a)
		var length: float = cross.length()
		# A collapsed triangle has no facing to judge. `boxjunctions.py` drops
		# them at twice-area 1e-6, so one here is a rounding survivor rather
		# than a fold.
		if length <= 0.0:
			continue
		if cross.y / length < MIN_FACING_UP:
			inverted += 1
	if inverted == 0:
		return PackedStringArray()
	return PackedStringArray(
		[
			(
				"%s: %d of %d triangles do not face up. " % [where, inverted, triangles]
				+ "cull_back draws none of those — the boxes are invisible, not wrong-looking."
			)
		]
	)
