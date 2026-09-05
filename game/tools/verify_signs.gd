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
## 🔴 **Since `P5-2` the asset is a LIBRARY and the city is its placements.**
## `signs.glb` carries one mesh per drawn face variant plus a unit pole, and
## `signs_placements.json` stands each of them; the checks below grade both
## halves and the join between them, in both directions — a library mesh
## nothing stands and a placement naming no mesh both render as a missing
## sign, and a placement with a negative scale renders as no sign at all under
## `cull_back`. The material and winding checks are per library mesh, which is
## every plate in the city checked once.
##
## ⚠️ **Absence is a pass, and here that is not even unusual.** `P3-16` ships only
## the signs whose meaning is their *shape*; a region whose signs are all time
## plates and parking legends draws none and `city.json` names null. What stops
## that becoming a silent skip is `verify_city.gd`, whose `_check_documents`
## asserts a *named* signs asset exists and matches the path `generated_layer.gd`'s table gives it — so a
## manifest naming `signs.glb` with the file gone fails there.
extends SceneTree

const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const GeneratedPlacements = preload("res://scripts/city/generated_placements.gd")
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
## ⚠️ **Per lettered code since `P5-2`**: `signs_text_TS102` stands under every
## `TS102` plate. A region whose drawn faces carry no `text` layer ships no such
## mesh, and so does a city whose whitelist has none — which is the state
## `Texture memory: 0` describes and the default `Q63` insisted stay the default.

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


func _init() -> void:
	if not GeneratedLayer.is_present(GeneratedLayer.SIGNS):
		print("  skip  no %s shipped for this region" % GeneratedLayer.noun(GeneratedLayer.SIGNS))
		quit(0)
		return

	var packed: PackedScene = GeneratedLayer.load_layer(GeneratedLayer.SIGNS)
	if packed == null:
		# Present but unloadable, which is not the same as absent — the hint
		# about rebuilding would be the wrong advice here.
		printerr(
			(
				"  FAIL  %s exists but did not load as a scene"
				% GeneratedLayer.path(GeneratedLayer.SIGNS)
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
		print("  ok    ", GeneratedLayer.path(GeneratedLayer.SIGNS))
	quit(1 if not problems.is_empty() else 0)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []

	var instances: Array[Node] = scene_root.find_children("*", "MeshInstance3D", true, false)
	if instances.is_empty():
		problems.append("the library carries no MeshInstance3D")
		return problems

	var library: Dictionary[String, Mesh] = {}
	var lettered: bool = false
	for node: Node in instances:
		var instance := node as MeshInstance3D
		var mesh := instance.mesh as ArrayMesh
		if mesh == null:
			problems.append("'%s' carries no ArrayMesh" % instance.name)
			continue
		library[String(instance.name)] = mesh
		if mesh.get_surface_count() != SURFACES_PER_MESH:
			problems.append(
				(
					"'%s' has %d surfaces, expected %d"
					% [instance.name, mesh.get_surface_count(), SURFACES_PER_MESH]
				)
			)
		if String(instance.name).begins_with(GeneratedLayer.SIGNS_TEXT_MESH):
			lettered = true
			problems.append_array(_check_lettering(mesh, instance.name))
		else:
			problems.append_array(_check_plates(mesh, instance.name))

	# ⚠️ Reported rather than required. A region with no `TS102` in it draws no
	# lettering and is right not to — see `GeneratedLayer.SIGNS_TEXT_ATLAS_BUDGET_PX`.
	if not lettered:
		print("  note  no lettering mesh; this region's faces carry no words")

	problems.append_array(_check_placements(library))
	problems.append_array(_check_has_no_collision(scene_root))
	return problems


## The join between the library and its placements, both ways, plus the one
## property of a transform that decides whether a plate draws at all.
##
## 🔴 **A negative scale is a mirror, and under `cull_back` a mirrored plate is
## a missing one.** The ETL draws a mirrored deviation board as its own mesh for
## exactly that reason, so no placement may carry the flip — and the refusal
## lives in `GeneratedPlacements.placement_of`, which returns null for a
## negative or zero factor, so that the preview cannot draw one either. Here
## that null is a failure. ⚠️ Reachable, and checked by mutation rather than
## read: negate one factor in `signs_placements.json` and this fails. There is
## deliberately no determinant check beside it — the basis is a compass
## rotation and a positive scale by construction, so one would read clean
## whatever the document said. `GeneratedPlacements.group` is the one statement
## of the join, shared with `layer_preview.gd`, so the two cannot disagree
## about which entries stand.
func _check_placements(library: Dictionary[String, Mesh]) -> PackedStringArray:
	var problems: PackedStringArray = []
	var document: Dictionary = GeneratedPlacements.load_placements(
		GeneratedLayer.placements_path(GeneratedLayer.SIGNS),
		GeneratedLayer.noun(GeneratedLayer.SIGNS)
	)
	if document.is_empty():
		problems.append("the library is present and its placements document is not")
		return problems
	var joined: Dictionary = GeneratedPlacements.group(document, library)
	if int(joined["no_mesh"]) > 0:
		problems.append("%d placements name a mesh the library does not carry" % joined["no_mesh"])
	if int(joined["no_transform"]) > 0:
		problems.append("%d placements carry no usable transform" % joined["no_transform"])
	for mesh_name: String in joined["unstood"] as PackedStringArray:
		problems.append("library mesh '%s' is stood nowhere" % mesh_name)
	if problems.is_empty():
		var entries: Array = document.get("placements", []) as Array
		print("  ok    %d placements stand %d library meshes" % [entries.size(), library.size()])
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
		problems.append_array(
			MeshContract.check_stands_upright(
				mesh, surface, where, "signs", "Signs are plates and posts", 0.5
			)
		)
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
				mesh, surface, where, true, GeneratedLayer.SIGNS_TEXT_ATLAS_BUDGET_PX
			)
		)
		problems.append_array(
			MeshContract.check_shader_source(
				mesh, surface, where, SIGNS_TEXT_SHADER, SIGNS_TEXT_MATERIAL
			)
		)
		problems.append_array(
			MeshContract.check_stands_upright(
				mesh, surface, where, "signs", "Signs are plates and posts", 0.5
			)
		)
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
		scene_root, "the signs", "SIGNS_POLE_MESH_NAME and the face codes in etl/pipeline/signs.py"
	)
