## Checks the generated turn arrows against the data contract, headless.
##
## `P3-15` delivers TD's published marking symbols as geometry rather than as
## paint on the ribbon, and the facts that decision rests on are engine-side:
## whether the importer dispatched the shader on the material name, whether it
## built a collider it must *not* have, and — the one that matters most —
## whether every triangle still faces the sky. Run:
##
##     godot --headless --path game --script res://tools/verify_arrows.gd
##
## Exits non-zero if the arrows are present and fail any check.
##
## ⚠️ **Absence is a pass, and that is not a loophole.** A city whose estate
## publishes no marking symbols ships none and `city.json` names null, so this
## cannot treat a missing asset as a failure without failing every such city.
## What stops that becoming a silent skip is `verify_city.gd`, whose
## `_check_documents` asserts a *named* arrows asset exists and matches this
## file's constant — so a manifest naming `arrows.glb` with the file gone fails
## there. ⚠️ `verify_tramway.gd` records that its version of that
## cross-reference was written before the check existed and stood wrong for a
## while. This one was written with it; if this comment is edited, go and look.
extends SceneTree

const GeneratedArrows = preload("res://scripts/city/generated_arrows.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")

## One primitive, so the whole region's arrows cost one draw call — the rule the
## road surface, the tiles and the tramway are all held to.
const SURFACES: int = 1

## The material the arrows must end up with, mirroring `SHADERS` in
## `tools/generated_scene_import.gd` and `ARROWS_MATERIAL` in
## `etl/pipeline/arrows.py`.
##
## Checked because the dispatch has **no failing state**: arrows that kept their
## imported `BaseMaterial3D` would be the right glyphs in the right places in
## whatever colour the importer chose, and nothing else here would notice.
const ARROWS_MATERIAL: String = "res://tuning/arrows.tres"

## How far a triangle may tilt off horizontal before it is a fold rather than a
## slope. Arrows are laid on the deck and take its grade, and the steepest street
## in the region is well inside this; what it catches is a triangle at or past
## vertical, which is a winding failure.
const MIN_FACING_UP: float = 0.1


func _init() -> void:
	if not GeneratedArrows.is_present():
		print("  skip  no turn arrows shipped for this region")
		quit(0)
		return

	var packed: PackedScene = GeneratedArrows.load_arrows()
	if packed == null:
		# Present but unloadable, which is not the same as absent — the hint
		# about rebuilding would be the wrong advice here.
		printerr("  FAIL  %s exists but did not load as a scene" % GeneratedArrows.PATH)
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
		print("  ok    ", GeneratedArrows.PATH)
	quit(1 if not problems.is_empty() else 0)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []

	var mesh: ArrayMesh = MeshContract.single_primitive(scene_root, SURFACES, problems)
	if mesh == null:
		return problems

	for surface: int in mesh.get_surface_count():
		var where: String = "surface %d" % surface
		# `false`: this mesh ships no `COLOR_0` on purpose — see `ARROWS_MATERIAL`
		# above and `config.Arrows`. Every other guarantee in `check_surface`
		# still applies, the no-texture one especially.
		problems.append_array(MeshContract.check_surface(mesh, surface, where, false))
		problems.append_array(
			MeshContract.check_shader_material(mesh, surface, where, ARROWS_MATERIAL)
		)
		problems.append_array(_check_faces_up(mesh, surface, where))

	problems.append_array(_check_has_no_collision(scene_root))
	return problems


## Paint must **not** collide, for the reason the tramway must not.
##
## Sharper here than there: an arrow lies flat across a lane the car is meant to
## drive along, so a collider would be a 15 mm step every vehicle in the region
## crosses at speed — and the whole guard against it is the absence of a `-col`
## suffix in one string in `arrows.py`.
func _check_has_no_collision(scene_root: Node3D) -> PackedStringArray:
	return MeshContract.check_no_collision(
		scene_root, "the arrows", "ARROWS_MESH_NAME in etl/pipeline/arrows.py"
	)


## Every triangle faces the sky (`P3-15`).
##
## ⚠️ **This asset's version of the failure that fails to nothing**, and the one
## this tool mainly exists for. `arrows.gdshader` is `cull_back`, so winding
## decides visibility and the normal attribute does not: a mesh wound the other
## way is correct geometry, in the correct place, with the correct material, and
## the city simply has no arrows in it. The tramway shipped exactly that —
## **5,111 of 5,112** triangles facing the ground — and no frame showed it.
##
## Checked here as well as in `arrows.json` because the two catch different
## things. The ETL's `inverted` counts what `pipeline/arrows.py` built; this
## counts what Godot imported, and an import that mirrors an axis moves one
## without the other.
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
		# them counter-clockwise** — so the importer reverses every index
		# triple, and an up-facing surface arrives with `(b-a)x(c-a)` pointing
		# *down*. The ETL's `downward_facing` tests the same expression with the
		# opposite sign, and both are right about their own side of the import.
		#
		# ⚠️ **Established by measurement, not from the documentation**, because
		# a sign convention read out of a manual is exactly the kind of claim
		# `Q57` and `Q58` were each written about. Two shipped meshes that
		# demonstrably render — `roads.glb` at **32,222 of 32,233** and
		# `tram.glb` at **5,132 of 5,132** — both point down here. The 11 that
		# do not are `roads.glb`'s known inward folds, which `Q54` counted
		# independently at 11 and 2.41 m2. If this ever needs revisiting,
		# re-measure against those two rather than re-reading this comment.
		var cross: Vector3 = (a - b).cross(c - a)
		var length: float = cross.length()
		# A collapsed triangle has no facing to judge. `arrows.py` drops them at
		# twice-area 1e-6, so one here is a rounding survivor rather than a fold.
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
				+ "cull_back draws none of those — the arrows are invisible, not wrong-looking."
			)
		]
	)
