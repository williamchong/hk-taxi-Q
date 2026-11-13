## Instantiates one of the ETL's one-mesh layers, for looking at the city
## (`P5-1`). `layer` names a row of `generated_layer.gd`'s table.
##
## A dev tool, not the streamer. Each of these layers is region-wide — the
## tramway as one mesh; the road marks, the boxes and the crossings as a mesh
## per plan cell, so the engine can cull what was 72,356 + 20,642 triangles
## from anywhere (`P3-40`, `P3-42`, `Q135`); the
## signs, the lamps, the arrows and the railings as a library of props stood by
## a placements document (`Q115`) — so there is nothing to stream, and
## deliberately nothing to LOD: `Q34`'s vertex clustering annihilates
## anything thinner than a cell, and a 90 mm column, a 100 mm hatch line or a
## 40 mm fence is exactly that.
##
## No transform is applied: every stage writes vertices in **region** game space,
## so a node at the origin already lines up with the buildings, the ribbon and
## the kerb it was joined to. That alignment is load-bearing for the paint in a
## way it is not for the rest — an arrow offset by a metre sits across a lane
## divider rather than between two.
##
## 🔴 **A node for a layer existing at all is `Q73`, and it has been missed
## twice.** `roadmarks.glb` was built, exported, synced, imported, graded by its
## own verify tool and drawn *nowhere* — `check.sh` green throughout, because a
## verify tool asks "is this asset correct" and never "is this asset on screen".
## The lamps then repeated it while quoting it: the node went into
## `city_preview.tscn` and not `city_drive.tscn`, which is the scene the game
## boots into, so the layer was correct, verified, visible in every preview shot
## and absent from the game until someone drove it. **A drawn layer needs a node
## in BOTH scenes, in the same commit as the asset** — and nothing but looking
## will tell you it does.
##
## ⚠️ **Absence is a report here, never a failure.** A city whose estate
## publishes no tramway ships none. The one required layer — the road, which is
## also the one that collides — is not a row of this table since `P5-6`: it
## streams with the tiles, and `tile_preview.gd` draws it in the preview scene.
## The table's `absence` sentence is kept so a required row could return.
##
## The collider count is printed because for every layer here but one there
## must be **none**, and each layer's reason is its own — they live in
## `region.md` beside the scene, under the node that would have to change
## (`Q74`, `Q119`). The exceptions are the placer's, never the asset's: the
## railings' box a placement (`collides`, `Q159`), the trees' trunks
## (`trunks`), and the lamps' and the signs' posts (`posts`, `Q191`).
extends Node3D

const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const MeshMeasure = preload("res://scripts/city/mesh_measure.gd")
const PropBatch = preload("res://scripts/city/prop_batch.gd")
const GeneratedPlacements = preload("res://scripts/city/generated_placements.gd")
const LampPools = preload("res://scripts/city/lamp_pools.gd")

## Emitted once built, with the bounds of the layer, so a camera can frame it.
signal built(low: Vector3, high: Vector3)

## A key of `GeneratedLayer.LAYERS`, set on the node in the scene. A string
## rather than one of the loader's constants because that is what a `.tscn`
## can store; `verify_city.gd` holds both scenes' values against `ids()`.
@export var layer: String = ""

## Which synced region's copy of the layer; "" is `GeneratedRegions.selected()`.
## Set by `CityRegions` before the node enters the tree (`P5-9c`).
@export var region: String = ""

## Stand a box body under every placement of a prop layer, from each library
## mesh's own extent. Off for every layer but the railings; the scene's sidecar
## says why per node. Ignored on a layer that is not a library.
@export var collides: bool = false

## Stand a trunk cylinder under every placement from the document's `trunks`
## table (`P3-77`): one static body per plan cell holding a shape per tree,
## because Jolt's 10,240 bodies already hold the railings' 7,693 and a body a
## tree would pass it. On for the trees alone; `region.md` says why.
@export var trunks: bool = false

## Stand an upright cylinder up the post of every placement whose library mesh
## is drawn standing on its origin — a lamp column, a sign pole — read off the
## mesh's own foot (`PropBatch.post_of`), one static body per plan cell for
## `trunks`' reason. A mesh that hangs (a sign's face) stands nothing: the post
## it hangs on is the obstacle. On for the lamps and the signs; `region.md`
## says why.
@export var posts: bool = false

## The one figure worth printing beyond the plan extent: a column has a height
## and a painted arrow does not. The preview's own formatting, kept out of the
## loader's table.
const _HEIGHT: Dictionary[String, String] = {
	GeneratedLayer.RAILINGS: "tall",
	GeneratedLayer.LAMPS: "tall",
	GeneratedLayer.TREES: "tall",
	GeneratedLayer.SIGNS: "tops",
}


func _ready() -> void:
	var at: String = GeneratedLayer.path(layer, region)
	if at.is_empty():
		push_error("layer_preview: %s names no generated layer" % name)
		return
	# Presence first, then load — `Q77`'s order, recorded on `is_present`.
	if not GeneratedLayer.is_present(layer, region):
		if GeneratedLayer.is_optional(layer):
			print("%s: none shipped for this region" % layer)
		else:
			push_warning(GeneratedLayer.missing_hint(layer))
		return
	var packed: PackedScene = GeneratedLayer.load_layer(layer, region)
	if packed == null:
		push_error("%s: %s exists but did not load as a scene" % [layer, at])
		return
	var instance: Node3D = packed.instantiate()
	var bounds: AABB
	var triangles: int
	if GeneratedLayer.has_placements(layer):
		# A library, not a scene: every mesh in it is a prop, and the document
		# says where each one stands (`P5-2`). The scene is read for its meshes
		# — the importer has already dispatched their materials — and freed.
		var placed: Dictionary = _place(instance)
		instance.free()
		if placed.is_empty():
			return
		bounds = placed["bounds"]
		triangles = int(placed["triangles"])
	else:
		if collides or posts:
			push_warning("%s: collides and posts stand bodies under a library's props only" % layer)
		instance.name = name
		add_child(instance)
		bounds = MeshMeasure.bounds(instance)
		triangles = MeshMeasure.triangles(instance)
		for found: Node in find_children("*", "GeometryInstance3D", true, false):
			if not GeneratedLayer.casts_shadow(layer, String(found.name)):
				(found as GeometryInstance3D).cast_shadow = (
					GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
				)
	var line: String = (
		"%s: %d triangles, %d colliders, spans %.0f x %.0f m"
		% [layer, triangles, MeshMeasure.colliders(self), bounds.size.x, bounds.size.z]
	)
	match _HEIGHT.get(layer, ""):
		"tall":
			line += ", %.1f m tall" % bounds.size.y
		"tops":
			line += ", tops out %.1f m" % bounds.end.y
	print(line)
	if bounds.size != Vector3.ZERO:
		# Deferred for the reason `tile_preview.gd` spells out: `_ready` runs
		# children-first, so a direct emit here beats the camera's connect.
		built.emit.call_deferred(bounds.position, bounds.end)


## Stands the library's meshes where the placements document puts them, one
## `MultiMesh` per mesh — per mesh and plan cell for a layer `prop_cells.tres`
## names — and returns the drawn extent and triangle count, or `{}` after
## pushing what went wrong.
##
## ⚠️ **Every library mesh must be stood at least once and every entry must
## name a mesh**, in both directions, and a miss is an error rather than a
## skip: a face in the library nothing stands is a code the ETL drew for
## nobody, and an entry naming no mesh is a sign that is not there. Neither
## shows in a frame. `GeneratedPlacements.group` is the one statement of that
## join; `verify_signs.gd` fails on the same counts this pushes.
func _place(library: Node3D) -> Dictionary:
	var meshes: Dictionary[String, Mesh] = _meshes_by_name(library)
	var document: Dictionary = GeneratedPlacements.load_placements(
		GeneratedLayer.placements_path(layer, region), GeneratedLayer.noun(layer)
	)
	if document.is_empty():
		return {}
	var joined: Dictionary = GeneratedPlacements.group(document, meshes)
	if int(joined["no_mesh"]) > 0:
		push_error("%s: %d placements name no library mesh" % [layer, joined["no_mesh"]])
	if int(joined["no_transform"]) > 0:
		push_error("%s: %d placements carry no usable transform" % [layer, joined["no_transform"]])
	for mesh_name: String in joined["unstood"] as PackedStringArray:
		push_error("%s: library mesh %s is stood nowhere" % [layer, mesh_name])
	var transforms: Dictionary[String, Array] = joined["transforms"]
	var tints: Dictionary[String, PackedColorArray] = joined["tints"]
	var trunk_table: Dictionary = document.get("trunks", {}) if trunks else {}
	if trunks and trunk_table.is_empty():
		push_error("%s: trunks is on and the document carries no trunks table" % layer)
	var boxes: Array[AABB] = []
	var posted: int = 0
	var triangles: int = 0
	var batches: int = 0
	var cells := load(PropCellProfile.PATH) as PropCellProfile
	if cells == null or layer not in cells.layers:
		cells = null
	elif cells.cell_m <= 0.0:
		push_error("%s: %s cuts it into cells of no size" % [layer, PropCellProfile.PATH])
		cells = null
	if trunks and cells == null:
		# Every trunk in one body is the body cap's argument lost, not a crash.
		push_warning(
			"%s: trunks stand uncut, one body a kind; add it to %s" % [layer, PropCellProfile.PATH]
		)
	for mesh_name: String in transforms:
		var mesh: Mesh = meshes[mesh_name]
		var batch: Array[Transform3D] = []
		batch.assign(transforms[mesh_name])
		var casts: bool = GeneratedLayer.casts_shadow(layer, mesh_name)
		var tint: PackedColorArray = tints.get(mesh_name, PackedColorArray())
		for node: MultiMeshInstance3D in PropBatch.batches(mesh, batch, mesh_name, cells, tint):
			if not casts:
				node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			add_child(node)
			batches += 1
		var local: AABB = mesh.get_aabb()
		for at: Transform3D in batch:
			boxes.append(at * local)
		if collides:
			if not local.has_volume():
				push_error("%s: library mesh %s is flat and cannot collide" % [layer, mesh_name])
			for body: StaticBody3D in PropBatch.bodies(local, batch, mesh_name + "_col"):
				add_child(body)
		if posts:
			var post: AABB = PropBatch.post_of(mesh)
			if post.has_volume():
				posted += batch.size()
				for body: StaticBody3D in PropBatch.posts(post, batch, mesh_name + "_posts", cells):
					add_child(body)
		if trunk_table.is_empty():
			pass
		elif not trunk_table.has(mesh_name):
			push_error("%s: library mesh %s has no trunk in the document" % [layer, mesh_name])
		else:
			for body: StaticBody3D in _stand_trunks(
				trunk_table[mesh_name], batch, mesh_name, cells
			):
				add_child(body)
		triangles += batch.size() * MeshMeasure.mesh_triangles(mesh)
		if layer == GeneratedLayer.LAMPS:
			batches += _stand_pools(mesh, batch, mesh_name, cells)
	if posts and posted == 0:
		push_error("%s: posts is on and no library mesh stands on a post" % layer)
	print(
		(
			"%s: %d placements over %d library meshes, %d batches"
			% [layer, document.get("placements", []).size(), meshes.size(), batches]
		)
	)
	return {"bounds": MeshMeasure.union(boxes), "triangles": triangles}


## A trunk cylinder under each of `batch`'s trees, one static body per plan
## cell (or one for the batch without `cells`). `trunk` is the kind's radius
## and height in the library's frame; each tree's stand scales both, and the
## shape stands upright whatever the tree's bearing.
func _stand_trunks(
	trunk: Dictionary, batch: Array[Transform3D], mesh_name: String, cells: PropCellProfile
) -> Array[StaticBody3D]:
	var radius_m: float = float(trunk.get("radius_m", 0.0))
	var height_m: float = float(trunk.get("height_m", 0.0))
	var bodies: Array[StaticBody3D] = []
	if radius_m <= 0.0 or height_m <= 0.0:
		push_error("%s: %s's trunk has no size" % [layer, mesh_name])
		return bodies
	# `trees.py` stands a tree at (across, up, across): a crown is round in
	# plan, so the trunk widens with its across-scale and rises with its up —
	# `PropBatch.posts`' own reading of a stand.
	var trunk_post := AABB(
		Vector3(-radius_m, 0.0, -radius_m), Vector3(2.0 * radius_m, height_m, 2.0 * radius_m)
	)
	return PropBatch.posts(trunk_post, batch, mesh_name + "_trunks", cells)


## The pool of light under each of `columns`' lanterns (`Q160`), on the lamps'
## own cells, and how many batches that added. Nothing — and a warning — for a
## library mesh that marks no lantern, or with the pools' material missing.
func _stand_pools(
	mesh: Mesh, columns: Array[Transform3D], mesh_name: String, cells: PropCellProfile
) -> int:
	var material := load(LampPools.MATERIAL_PATH) as ShaderMaterial
	var lantern: Vector3 = LampPools.lantern_of(mesh)
	if material == null or lantern == Vector3.INF:
		push_warning("%s: %s throws no pool of light at night" % [layer, mesh_name])
		return 0
	var pools: Array[Transform3D] = LampPools.stand(
		columns, lantern, material.get_shader_parameter(&"drop_m")
	)
	var stood: Array[MultiMeshInstance3D] = PropBatch.batches(
		LampPools.cylinder(material), pools, mesh_name + "_pool", cells
	)
	for node: MultiMeshInstance3D in stood:
		node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(node)
	return stood.size()


## The library's meshes by the name the ETL gave each — the importer has
## already dispatched their materials.
func _meshes_by_name(library: Node3D) -> Dictionary[String, Mesh]:
	var meshes: Dictionary[String, Mesh] = {}
	for node: Node in library.find_children("*", "MeshInstance3D", true, false):
		var found := node as MeshInstance3D
		if found.mesh != null:
			meshes[String(found.name)] = found.mesh
	return meshes
