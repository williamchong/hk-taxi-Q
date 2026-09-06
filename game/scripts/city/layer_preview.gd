## Instantiates one of the ETL's one-mesh layers, for looking at the city
## (`P5-1`). `layer` names a row of `generated_layer.gd`'s table.
##
## A dev tool, not the streamer. Each of these layers is region-wide — the
## carriageway, the tramway, the boxes, the stop lines, the signals and the
## railings as one mesh each; the signs, the lamps and the arrows as a library
## of props stood by a placements document (`Q115`) — so there is nothing to
## stream, and deliberately nothing to LOD: `Q34`'s vertex clustering annihilates
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
## ⚠️ **Absence is a warning for the road surface and a report for everything
## else.** Nothing under the start line means the build went wrong; a city whose
## estate publishes no tramway ships none. The table's `absence` sentence is what
## tells the two apart, so this script does not have to.
##
## The collider count is printed because for every layer but the road surface
## there must be **none**, and each layer's reason is its own — they live in
## `city_drive.md` and `city_preview.md` beside those scenes, under the node
## that would have to change (`Q74`, `Q119`).
extends Node3D

const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")
const PropBatch = preload("res://scripts/city/prop_batch.gd")
const GeneratedPlacements = preload("res://scripts/city/generated_placements.gd")

## Emitted once built, with the bounds of the layer, so a camera can frame it.
signal built(low: Vector3, high: Vector3)

## A key of `GeneratedLayer.LAYERS`, set on the node in the scene. A string
## rather than one of the loader's constants because that is what a `.tscn`
## can store; `verify_city.gd` holds both scenes' values against `ids()`.
@export var layer: String = ""

## The one figure worth printing beyond the plan extent: a column has a height
## and a painted arrow does not. The preview's own formatting, kept out of the
## loader's table.
const _HEIGHT: Dictionary[String, String] = {
	GeneratedLayer.RAILINGS: "tall",
	GeneratedLayer.LAMPS: "tall",
	GeneratedLayer.SIGNS: "tops",
}


func _ready() -> void:
	var at: String = GeneratedLayer.path(layer)
	if at.is_empty():
		push_error("layer_preview: %s names no generated layer" % name)
		return
	# Presence first, then load — `Q77`'s order, recorded on `is_present`.
	if not GeneratedLayer.is_present(layer):
		if GeneratedLayer.is_optional(layer):
			print("%s: none shipped for this region" % layer)
		else:
			push_warning(GeneratedLayer.missing_hint(layer))
		return
	var packed: PackedScene = GeneratedLayer.load_layer(layer)
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
		instance.name = name
		add_child(instance)
		bounds = MeshContract.bounds(instance)
		triangles = MeshContract.triangles(instance)
	var line: String = (
		"%s: %d triangles, %d colliders, spans %.0f x %.0f m"
		% [layer, triangles, MeshContract.colliders(self), bounds.size.x, bounds.size.z]
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
## `MultiMesh` per mesh, and returns the drawn extent and triangle count — or
## `{}` after pushing what went wrong.
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
		GeneratedLayer.placements_path(layer), GeneratedLayer.noun(layer)
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
	var boxes: Array[AABB] = []
	var triangles: int = 0
	for mesh_name: String in transforms:
		var mesh: Mesh = meshes[mesh_name]
		var batch: Array[Transform3D] = []
		batch.assign(transforms[mesh_name])
		add_child(PropBatch.batch(mesh, batch, mesh_name))
		var local: AABB = mesh.get_aabb()
		for at: Transform3D in batch:
			boxes.append(at * local)
		triangles += batch.size() * MeshContract.mesh_triangles(mesh)
	print(
		(
			"%s: %d placements over %d library meshes, %d draw calls"
			% [layer, document.get("placements", []).size(), meshes.size(), transforms.size()]
		)
	)
	return {"bounds": MeshContract.union(boxes), "triangles": triangles}


## The library's meshes by the name the ETL gave each — the importer has
## already dispatched their materials.
func _meshes_by_name(library: Node3D) -> Dictionary[String, Mesh]:
	var meshes: Dictionary[String, Mesh] = {}
	for node: Node in library.find_children("*", "MeshInstance3D", true, false):
		var found := node as MeshInstance3D
		if found.mesh != null:
			meshes[String(found.name)] = found.mesh
	return meshes
