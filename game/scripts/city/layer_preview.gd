## Instantiates one of the ETL's one-mesh layers, for looking at the city
## (`P5-1`). `layer` names a row of `generated_layer.gd`'s table.
##
## A dev tool, not the streamer. Each of these layers is one mesh for the whole
## region — the carriageway, the tramway, the arrows, the boxes, the stop lines,
## the signals, the railings, the lamps, the signs — so there is nothing to
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
## the node comments of `city_drive.tscn` and `city_preview.tscn`, beside the
## node that would have to change (`Q74`).
extends Node3D

const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")

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
	instance.name = name
	add_child(instance)
	var bounds: AABB = MeshContract.bounds(instance)
	var line: String = (
		"%s: %d triangles, %d colliders, spans %.0f x %.0f m"
		% [
			layer,
			MeshContract.triangles(instance),
			MeshContract.colliders(instance),
			bounds.size.x,
			bounds.size.z,
		]
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
