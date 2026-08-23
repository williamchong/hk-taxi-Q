## Checks the generated traffic signs against the data contract, headless.
##
## `P3-16` delivers TD's published signs as geometry standing on the poles the
## publisher surveyed, and the facts that decision rests on are engine-side:
## whether the importer dispatched the shader on the material name, whether it
## built a collider it must *not* have, and whether every triangle still faces
## the way it was wound to. Run:
##
##     godot --headless --path game --script res://tools/verify_signs.gd
##
## Exits non-zero if the signs are present and fail any check.
##
## ⚠️ **Absence is a pass, and here that is not even unusual.** `P3-16` ships only
## the signs whose meaning is their *shape*; a region whose signs are all time
## plates and parking legends draws none and `city.json` names null. What stops
## that becoming a silent skip is `verify_city.gd`, whose `_check_documents`
## asserts a *named* signs asset exists and matches this file's constant — so a
## manifest naming `signs.glb` with the file gone fails there.
extends SceneTree

const GeneratedSigns = preload("res://scripts/city/generated_signs.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")

## One surface per mesh, so each primitive is one draw call — the rule the road
## surface, the tiles, the tramway and the arrows are all held to.
##
## ⚠️ **Held despite the layer having four colours**, which is the thing that
## would most plausibly have split it. It does not, because the colour rides
## `COLOR_0` rather than a material per livery — see `signs.gdshader`.
const SURFACES_PER_MESH: int = 1

## 🔴 **What DID split the layer, and it is the vertex layout rather than the
## look** (`P3-20`). A face with words on it needs `TEXCOORD_0`, `mesh.py`
## refuses to merge a mesh that has UVs with one that does not, and putting the
## channel on the whole asset would charge 36,616 vertices to serve 74 plates. So
## the lettering is a second primitive: one extra draw call, and the untextured
## majority byte-identical.
##
## ⚠️ **Two is the maximum and one is normal.** A region whose drawn faces carry
## no `text` layer ships the plate mesh alone, and so does a city whose whitelist
## has none — which is the state `Texture memory: 0` describes and the default
## `Q63` insisted stay the default.
const MAX_MESHES: int = 2

## The material the lettering must end up with, mirroring `TEXTURED` in
## `tools/generated_scene_import.gd` and `SIGNS_TEXT_MATERIAL` in
## `etl/pipeline/signs.py`.
##
## ⚠️ **Checked through its SHADER, not its resource path.** This one material is
## duplicated at import so it can hold a per-region texture, and a duplicate has
## no `resource_path` — see `MeshContract.check_shader_source`.
const SIGNS_TEXT_MATERIAL: String = "res://tuning/signs_text.tres"
const SIGNS_TEXT_SHADER: String = "res://assets/shaders/signs_text.gdshader"

## The material the signs must end up with, mirroring `SHADERS` in
## `tools/generated_scene_import.gd` and `SIGNS_MATERIAL` in
## `etl/pipeline/signs.py`.
##
## ⚠️ **Checked because this dispatch fails *quietly*, unlike the arrows'.** An
## arrow that kept its imported `BaseMaterial3D` is visibly the wrong grey. A
## sign that kept its own still draws the right plates in the right colours,
## because the livery is on the vertex — it just loses
## `vertex_srgb_to_linear`, so the whole city's signage renders pale. `Q27`
## measured what that costs and why no ambient tuning recovers it. Nothing but
## this check would notice.
const SIGNS_MATERIAL: String = "res://tuning/signs.tres"

## How near horizontal a triangle's normal must be to count as part of a plate
## or a post.
##
## ⚠️ **This is the inverse of `verify_arrows.gd`'s `MIN_FACING_UP`, and the
## inversion is the point.** An arrow lies on the deck, so "faces the sky" is its
## correctness condition. A sign plate stands upright and a pole is a vertical
## prism, so the overwhelming majority of this mesh faces *sideways* — a sign
## mesh graded by the arrows' rule would fail every triangle it should pass.
## Pole caps are the legitimate exception and are counted separately.
const MAX_UPRIGHT_Y: float = 0.35


func _init() -> void:
	if not GeneratedSigns.is_present():
		print("  skip  no traffic signs shipped for this region")
		quit(0)
		return

	var packed: PackedScene = GeneratedSigns.load_signs()
	if packed == null:
		# Present but unloadable, which is not the same as absent — the hint
		# about rebuilding would be the wrong advice here.
		printerr("  FAIL  %s exists but did not load as a scene" % GeneratedSigns.PATH)
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
		print("  ok    ", GeneratedSigns.PATH)
	quit(1 if not problems.is_empty() else 0)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []

	var instances: Array[Node] = scene_root.find_children("*", "MeshInstance3D", true, false)
	if instances.is_empty() or instances.size() > MAX_MESHES:
		problems.append(
			"expected 1 or %d MeshInstance3D, found %d" % [MAX_MESHES, instances.size()]
		)
		return problems

	var lettered: bool = false
	for node: Node in instances:
		var instance := node as MeshInstance3D
		var mesh := instance.mesh as ArrayMesh
		if mesh == null:
			problems.append("'%s' carries no ArrayMesh" % instance.name)
			continue
		if mesh.get_surface_count() != SURFACES_PER_MESH:
			problems.append(
				(
					"'%s' has %d surfaces, expected %d"
					% [instance.name, mesh.get_surface_count(), SURFACES_PER_MESH]
				)
			)
		if String(instance.name) == GeneratedSigns.TEXT_MESH:
			lettered = true
			problems.append_array(_check_lettering(mesh, instance.name))
		else:
			problems.append_array(_check_plates(mesh, instance.name))

	# ⚠️ Reported rather than required. A region with no `TS102` in it draws no
	# lettering and is right not to — see `GeneratedSigns.TEXT_ATLAS_BUDGET_PX`.
	if not lettered:
		print("  note  no lettering primitive; this region's faces carry no words")

	problems.append_array(_check_has_no_collision(scene_root))
	return problems


## The plates and posts: the layer as it was before `P3-20`.
func _check_plates(mesh: ArrayMesh, name: StringName) -> PackedStringArray:
	var problems: PackedStringArray = []
	for surface: int in mesh.get_surface_count():
		var where: String = "'%s' surface %d" % [name, surface]
		# `true`: this mesh **does** ship `COLOR_0`, and it is the only generated
		# road-furniture mesh that does — a plate is four colours in one draw
		# call. `arrows.glb` passes `false` here for the opposite reason.
		#
		# ⚠️ **No budget argument, so the texture refusal is the absolute one.**
		# This surface must stay imageless however many the lettering ships, and
		# saying nothing here is what says so (`Q63`).
		problems.append_array(MeshContract.check_surface(mesh, surface, where, true))
		problems.append_array(
			MeshContract.check_shader_material(mesh, surface, where, SIGNS_MATERIAL)
		)
		problems.append_array(_check_stands_upright(mesh, surface, where))
	return problems


## The lettering quads, and the one surface in this bundle allowed an image.
##
## 🔴 **Every check here is against a failure that renders as a correct city.**
## A lettering quad whose texture never arrived samples white and vanishes into
## the plate; one whose material was not dispatched keeps its `BaseMaterial3D`
## and loses `Q27`'s conversion; one wound backwards draws nothing at all. None
## of the three moves a triangle count or an AABB.
func _check_lettering(mesh: ArrayMesh, name: StringName) -> PackedStringArray:
	var problems: PackedStringArray = []
	for surface: int in mesh.get_surface_count():
		var where: String = "'%s' surface %d" % [name, surface]
		if not (mesh.surface_get_format(surface) & Mesh.ARRAY_FORMAT_TEX_UV):
			# The whole reason this is a second primitive. Without UVs every quad
			# samples texel 0 and the plates come out uniformly tinted.
			problems.append("%s carries no UVs" % where)
		# 🔴 **The budget declaration** (`Q63`). Passing it is what admits an
		# image here at all, and it buys a ceiling: over budget fails, and a
		# declared texture that never arrived fails too.
		problems.append_array(
			MeshContract.check_surface(
				mesh, surface, where, true, GeneratedSigns.TEXT_ATLAS_BUDGET_PX
			)
		)
		problems.append_array(
			MeshContract.check_shader_source(
				mesh, surface, where, SIGNS_TEXT_SHADER, SIGNS_TEXT_MATERIAL
			)
		)
		problems.append_array(_check_stands_upright(mesh, surface, where))
	return problems


## Street furniture must **not** collide, for the reason the tramway must not.
##
## ⚠️ **The reasoning runs the other way from the arrows', and is weaker.** A
## painted arrow must not collide because a 15 mm step across every lane would be
## absurd. A sign pole is a real obstacle that a real car really would hit, so its
## absence here is a **budget** decision rather than a correctness one: 450 posts
## is 450 collision bodies, and `P2-6` has not measured a frame on the device
## floor. `GAME_DESIGN.md` puts breakaway posts in `B3`, and the whole guard
## against one arriving early is the absence of a `-col` suffix in one string.
func _check_has_no_collision(scene_root: Node3D) -> PackedStringArray:
	return MeshContract.check_no_collision(
		scene_root, "the signs", "SIGNS_MESH_NAME in etl/pipeline/signs.py"
	)


## The mesh stands upright (`P3-16`).
##
## ⚠️ **This asset's version of the failure that fails to nothing.**
## `signs.gdshader` is `cull_back`, so winding decides visibility and the normal
## attribute does not: a mesh wound the other way is correct geometry, in the
## correct place, with the correct material, and the city simply has no signs in
## it. The tramway shipped exactly that — **5,111 of 5,112** triangles facing the
## ground — and no frame showed it. This layer shipped its own version on the
## first build: **3,200** triangles, every pole in the region, because the prism
## ring was wound the way a plate wants.
##
## ⚠️ **A vertical surface cannot be graded by "which way is up", so this checks
## agreement instead**: every triangle's winding must agree with the normal it
## was given. That is the same question `pipeline/signs.py`'s `facing_away` asks —
## and it is asked twice because the two catch different things. The ETL counts
## what it built; this counts what Godot imported, and an import that mirrors an
## axis moves one without the other.
func _check_stands_upright(mesh: Mesh, surface: int, where: String) -> PackedStringArray:
	var arrays: Array = mesh.surface_get_arrays(surface)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	if indices.is_empty():
		return PackedStringArray(["%s carries no index buffer to check winding on" % where])
	if normals.is_empty():
		return PackedStringArray(["%s carries no normals to check winding against" % where])

	var disagreeing: int = 0
	var upright: int = 0
	# `floori` of a float divide rather than an integer one: GDScript warns on
	# integer division and `check.sh` promotes warnings to errors, so the plain
	# form does not compile. The count is exact — an index buffer is always a
	# multiple of three.
	var triangles: int = floori(indices.size() / 3.0)
	for triangle: int in triangles:
		var ia: int = indices[triangle * 3]
		var a: Vector3 = vertices[ia]
		var b: Vector3 = vertices[indices[triangle * 3 + 1]]
		var c: Vector3 = vertices[indices[triangle * 3 + 2]]
		# ⚠️ **Negated, because Godot winds front faces clockwise and glTF winds
		# them counter-clockwise** — so the importer reverses every index triple.
		# `verify_arrows.gd` records how that sign was established: by measuring
		# two shipped meshes that demonstrably render, not by reading a manual.
		# ⚠️ **Do not "fix" this to agree with the ETL's `facing_away`**, which
		# tests the same expression with the opposite sign; `Q59` records that
		# both are right about their own side of the import.
		var cross: Vector3 = (a - b).cross(c - a)
		var length: float = cross.length()
		# A collapsed triangle has no facing to judge. `signs.py` drops them at
		# twice-area 1e-6, so one here is a rounding survivor rather than a fold.
		if length <= 0.0:
			continue
		if cross.dot(normals[ia]) < 0.0:
			disagreeing += 1
		if absf(cross.y / length) <= MAX_UPRIGHT_Y:
			upright += 1

	var problems: PackedStringArray = []
	if disagreeing > 0:
		problems.append(
			(
				(
					"%s: %d of %d triangles are wound against their own normal. "
					% [where, disagreeing, triangles]
				)
				+ "cull_back draws none of those — those signs are invisible, not wrong-looking."
			)
		)
	# A sign mesh is plates and posts, so most of it is vertical. If it is not,
	# something has been laid flat — which is what a plate drawn in the ground
	# plane looks like, and it would render as a sign-shaped decal on the footway
	# rather than as nothing.
	if triangles > 0 and upright * 2 < triangles:
		problems.append(
			(
				"%s: only %d of %d triangles stand upright. " % [where, upright, triangles]
				+ "Signs are plates and posts — a mostly-horizontal signs mesh has been laid flat."
			)
		)
	return problems
