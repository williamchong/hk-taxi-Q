## Instantiates the ETL's road surface, for looking at the city.
##
## A dev tool, not the streamer, exactly like `tile_preview.gd`. The whole
## region's carriageway is one mesh — 28k triangles for Wan Chai, against 989k
## for the massing — so there is nothing to stream and nothing to LOD.
##
## No transform is applied, for the same reason as the tiles: `surface.py`
## writes vertices in **region** game space, so a node at the origin already
## lines up with the buildings and with `road_preview.gd`'s graph.
extends Node3D

const GeneratedRoadSurface = preload("res://scripts/city/generated_road_surface.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")

## Emitted once built, with the bounds of the surface, so a camera can frame it.
signal built(low: Vector3, high: Vector3)


func _ready() -> void:
	var packed: PackedScene = GeneratedRoadSurface.load_surface()
	if packed == null:
		push_warning(GeneratedRoadSurface.missing_hint())
		return

	var surface: Node3D = packed.instantiate()
	surface.name = "RoadSurface"
	add_child(surface)

	var bounds: AABB = MeshContract.bounds(surface)
	var triangles: int = MeshContract.triangles(surface)

	# Printed because it is the number that says whether the `-col` suffix in
	# the mesh name did its job. Collision is a `P1-4` deliverable, and a road
	# you fall through looks identical to one you do not until you drive it.
	print(
		(
			"road surface: %d triangles, %d colliders, spans %.0f x %.0f m"
			% [
				triangles,
				surface.find_children("*", "StaticBody3D", true, false).size(),
				bounds.size.x,
				bounds.size.z,
			]
		)
	)
	if bounds.size != Vector3.ZERO:
		# Deferred for the reason `tile_preview.gd` spells out: `_ready` runs
		# children-first, so a direct emit here beats the camera's connect.
		built.emit.call_deferred(bounds.position, bounds.end)
