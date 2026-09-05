## Checks the generated pedestrian railings against the data contract, headless.
##
## `P3-19` delivers TD's published `DTAD_RAILING_LINE` as geometry standing on
## the kerb the ribbon actually drew, and the facts that decision rests on are
## engine-side: whether the importer dispatched the shader on the material name,
## whether it built a collider it must *not* have, whether the shader still
## draws both faces, and whether every quad still looks at the road. Run:
##
##     godot --headless --path game --script res://tools/verify_railings.gd
##
## Exits non-zero if the railings are present and fail any check.
##
## 🔴 **Since `P5-5` (`Q115`) the asset is a LIBRARY — one panel per class —
## and the city is `railings_placements.json`.** Every mesh check below runs on
## the panel, which is every panel in the city checked once: a stand is a
## rotation, and a rotation turns a quad's winding and its normal together, so
## the panel faces the road exactly when every copy of it does. The join is
## graded both ways by `GeneratedPlacements.check_join`, shared with the signs,
## the lamps and the arrows.
##
## ⚠️ **Absence is a pass, and that is not a loophole** — `verify_arrows.gd`'s
## paragraph, unchanged: a city whose estate publishes no railing layer ships
## none and `city.json` names null. What stops that becoming a silent skip is
## `verify_city.gd`, whose `_check_documents` asserts a *named* railing asset
## exists and matches the path `generated_layer.gd`'s table gives it.
extends SceneTree

const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const GeneratedPlacements = preload("res://scripts/city/generated_placements.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")

## One primitive **per class**, so each class costs one draw call — the rule the
## road surface, the tiles, the tramway, the arrows and the box junctions are
## all held to. Three classes is three draw calls, which is the price `Q61`
## records for keeping their geometry separable; a `MultiMesh` per class since
## `P5-5` costs the same three (`P3-29`).
const SURFACES_PER_CLASS: int = 1

## The classes the ETL draws, and the material each must end up with. Mirrors
## `classes:` in `etl/config/hong_kong.yaml` and `SHADERS` in
## `tools/generated_scene_import.gd`; the key is the class `id`, which is the
## glTF mesh name, the node name and the material name all at once.
##
## Checked because the dispatch has **no failing state**: fences that kept their
## imported `BaseMaterial3D` would be the right fences on the right kerbs in
## whatever colour the importer chose, and nothing else here would notice. Since
## `Q61` there is a second, sharper version of the same hazard — the three
## classes share one shader and differ **only** in their `.tres` mask numbers,
## so a bollard handed `railings.tres` is a picket fence standing where a
## bollard should be, and it renders perfectly.
const CLASS_MATERIALS: Dictionary = {
	"railings": "res://tuning/railings.tres",
	"bollards": "res://tuning/bollards.tres",
	"barriers": "res://tuning/barriers.tres",
}

## What the shader's render mode must say.
##
## ⚠️ **This asset's version of the failure that fails to nothing, and it is not
## the winding one.** Every other generated mesh here is `cull_back` and is
## checked for facing the sky. A fence is a single-quad vertical surface the car
## drives past on both sides, so it is drawn `cull_disabled` — and if that ever
## became `cull_back`, half of every street's railings would silently stop
## drawing depending on which way the road was digitised. Nothing else in this
## file, and nothing in `railings.json`, can see that: the mesh would be
## identical.
const CULL_MODE: String = "cull_disabled"

## How far a triangle's winding may disagree with the normal it was given.
##
## Zero tolerance in principle — the two are built from the same quad — but the
## dot product is normalised against float32 positions that Godot re-quantises
## on import, so the bar is "the wrong side of the surface" rather than "not
## exactly aligned".
const MIN_AGREEMENT: float = 0.0


func _init() -> void:
	if not GeneratedLayer.is_present(GeneratedLayer.RAILINGS):
		print(
			"  skip  no %s shipped for this region" % GeneratedLayer.noun(GeneratedLayer.RAILINGS)
		)
		quit(0)
		return

	var packed: PackedScene = GeneratedLayer.load_layer(GeneratedLayer.RAILINGS)
	if packed == null:
		# Present but unloadable, which is not the same as absent — the hint
		# about rebuilding would be the wrong advice here.
		printerr(
			(
				"  FAIL  %s exists but did not load as a scene"
				% GeneratedLayer.path(GeneratedLayer.RAILINGS)
			)
		)
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
		print("  ok    ", GeneratedLayer.path(GeneratedLayer.RAILINGS))
	quit(1 if not problems.is_empty() else 0)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []

	# One `MeshInstance3D` per class since `Q61`, each named for its class, so
	# `MeshContract.single_primitive` — which insists on exactly one — no longer
	# fits. What it was buying is kept: each class must still be one primitive.
	var instances: Array[Node] = scene_root.find_children("*", "MeshInstance3D", true, false)
	if instances.is_empty():
		problems.append("no MeshInstance3D in the railing scene")
		return problems

	var library: Dictionary[String, Mesh] = {}
	for node: Node in instances:
		var instance := node as MeshInstance3D
		var class_id: String = String(instance.name)
		if not CLASS_MATERIALS.has(class_id):
			# A class in the config with no row here would import with its
			# `BaseMaterial3D` and draw, so the mismatch has to fail loudly.
			problems.append(
				(
					"mesh '%s' is not a known railing class. " % class_id
					+ "CLASS_MATERIALS here, SHADERS in generated_scene_import.gd and "
					+ "`classes:` in hong_kong.yaml move together."
				)
			)
			continue

		var mesh := instance.mesh as ArrayMesh
		if mesh == null:
			problems.append("'%s' carries no ArrayMesh" % class_id)
			continue
		library[class_id] = mesh
		if mesh.get_surface_count() != SURFACES_PER_CLASS:
			problems.append(
				(
					"'%s' has %d surfaces, expected %d"
					% [class_id, mesh.get_surface_count(), SURFACES_PER_CLASS]
				)
			)

		problems.append_array(_check_class(mesh, class_id))

	problems.append_array(
		GeneratedPlacements.check_join(
			GeneratedLayer.placements_path(GeneratedLayer.RAILINGS),
			GeneratedLayer.noun(GeneratedLayer.RAILINGS),
			library
		)
	)
	problems.append_array(_check_has_no_collision(scene_root))
	return problems


## Problems with one class's mesh — the per-surface half of `_check`.
func _check_class(mesh: ArrayMesh, class_id: String) -> PackedStringArray:
	var problems: PackedStringArray = []
	for surface: int in mesh.get_surface_count():
		var where: String = "'%s' surface %d" % [class_id, surface]
		# `false`: these meshes ship no `COLOR_0` on purpose — see
		# `CLASS_MATERIALS` above and `config.Railings`. Every other guarantee
		# in `check_surface` still applies, the no-texture one especially.
		problems.append_array(MeshContract.check_surface(mesh, surface, where, false))
		problems.append_array(
			MeshContract.check_shader_material(
				mesh, surface, where, String(CLASS_MATERIALS[class_id])
			)
		)
		problems.append_array(_check_draws_both_faces(mesh, surface, where))
		problems.append_array(_check_faces_the_road(mesh, surface, where))
	return problems


## Railings must **not** collide, and here that is a design decision.
##
## `GAME_DESIGN.md` lists pedestrian railings under "deliberately diverge on —
## omit or make breakable", because Hong Kong's streets faithfully railed are a
## traffic simulator with no room to be reckless. Drawing them as scenery keeps
## the picture and keeps the divergence; a collider would quietly undo the
## second half. Breakaway is a `B3` question.
##
## ⚠️ **The guard used to be one string in `railings.py` and is now a config
## check.** Since `Q61` a mesh is named by its class `id` in `hong_kong.yaml`, so
## the `-col` suffix Godot's importer builds collision from could arrive from a
## city file; `config._railing_class` refuses an id ending in it. This is the
## second half of that guard, in the engine, where the collider would appear.
func _check_has_no_collision(scene_root: Node3D) -> PackedStringArray:
	return MeshContract.check_no_collision(
		scene_root, "the railings", "every class id in hong_kong.yaml `railings.classes`"
	)


## The shader still draws both faces (`P3-19`).
##
## Read off the shader's own source because that is the only channel Godot
## offers: `render_mode` is compiled into the `Shader`, not exposed as a
## property. Stringy, and worth it — the alternative is that a one-word edit to
## `railings.gdshader` deletes half the region's fences and every other check in
## this file, and every counter in `railings.json`, still passes.
func _check_draws_both_faces(mesh: Mesh, surface: int, where: String) -> PackedStringArray:
	var material: Material = mesh.surface_get_material(surface)
	var shaded: ShaderMaterial = material as ShaderMaterial
	if shaded == null or shaded.shader == null:
		# The material check above already reports this; saying it twice would
		# bury the finding that matters under a duplicate.
		return PackedStringArray()
	if shaded.shader.code.contains(CULL_MODE):
		return PackedStringArray()
	return PackedStringArray(
		[
			(
				"%s: the railing shader does not declare %s. " % [where, CULL_MODE]
				+ "A fence is one quad thick and the car passes it on both sides — "
				+ "back-face culling makes half of them invisible, not wrong-looking."
			)
		]
	)


## Every quad looks at the carriageway (`P3-19`).
##
## The vertical-surface counterpart of `verify_boxjunctions.gd`'s faces-up
## check, asking the question that matters for a fence: not "does this face the
## sky" but "does this face the road it was built to face". Under
## `cull_disabled` a flipped quad still draws — it draws lit from the wrong
## hemisphere, which reads as a black panel in full sun.
##
## Checked here as well as in `railings.json` because the two catch different
## things. The ETL's `facing_away` counts what `pipeline/railings.py` built;
## this counts what Godot imported, and an import that mirrors an axis moves one
## without the other.
func _check_faces_the_road(mesh: Mesh, surface: int, where: String) -> PackedStringArray:
	var arrays: Array = mesh.surface_get_arrays(surface)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	if indices.is_empty():
		return PackedStringArray(["%s carries no index buffer to check winding on" % where])
	if normals.is_empty():
		return PackedStringArray(["%s carries no normals to check the winding against" % where])

	var disagreeing: int = 0
	# `floori` of a float divide rather than an integer one: GDScript warns on
	# integer division and `check.sh` promotes warnings to errors, so the plain
	# form does not compile. The count is exact — an index buffer is always a
	# multiple of three.
	var triangles: int = floori(indices.size() / 3.0)
	for triangle: int in triangles:
		var first: int = indices[triangle * 3]
		var a: Vector3 = vertices[first]
		var b: Vector3 = vertices[indices[triangle * 3 + 1]]
		var c: Vector3 = vertices[indices[triangle * 3 + 2]]
		# ⚠️ **Negated, because Godot winds front faces clockwise and glTF winds
		# them counter-clockwise** — `verify_arrows.gd`'s expression, kept
		# verbatim. The sign was established by measurement against `roads.glb`
		# and `tram.glb`; if this ever needs revisiting, re-measure against those
		# two rather than re-reading this comment, and do not "fix" either side
		# to agree with the other (`Q59`).
		var cross: Vector3 = (a - b).cross(c - a)
		# A collapsed triangle has no facing to judge. `railings.py` drops them
		# at twice-area 1e-6, so one here is a rounding survivor rather than a
		# fold.
		if cross.length() <= 0.0:
			continue
		if cross.normalized().dot(normals[first]) <= MIN_AGREEMENT:
			disagreeing += 1
	if disagreeing == 0:
		return PackedStringArray()
	return PackedStringArray(
		[
			(
				(
					"%s: %d of %d triangles are wound away from their own normal. "
					% [where, disagreeing, triangles]
				)
				+ "cull_disabled still draws those — they light from the wrong side, "
				+ "which reads as a black panel and not as a missing one."
			)
		]
	)
