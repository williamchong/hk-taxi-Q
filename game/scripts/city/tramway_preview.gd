## Instantiates the ETL's tramway, for looking at the city.
##
## A dev tool, not the streamer, exactly like `road_surface_preview.gd`. The
## whole region's tramway is one mesh — ~5k triangles for Wan Chai, against 28k
## for the carriageway — so there is nothing to stream and nothing to LOD.
##
## No transform is applied, for the same reason as the road surface:
## `tramway.py` writes vertices in **region** game space, so a node at the
## origin already lines up with the ribbon and the buildings.
##
## ⚠️ **Absence is not a warning here.** A city whose estate publishes no
## tramway ships none (`P3-14`), so a missing asset prints what happened and
## returns. That is the opposite of the road surface, where nothing under the
## start line means the build went wrong.
extends Node3D

const GeneratedTramway = preload("res://scripts/city/generated_tramway.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")


func _ready() -> void:
	var packed: PackedScene = GeneratedTramway.load_tramway()
	if packed == null:
		print("tramway: none shipped for this region")
		return

	var tramway: Node3D = packed.instantiate()
	tramway.name = "Tramway"
	add_child(tramway)

	var bounds: AABB = MeshContract.bounds(tramway)

	# Colliders are printed for the opposite reason `road_surface_preview.gd`
	# prints them: the tramway must have **none**. It has no `-col` suffix, it
	# lies on ground that is already solid (`P3-10`), and a 30 mm rail modelled
	# as collision geometry is a kerb the player cannot see the point of.
	print(
		(
			"tramway: %d triangles, %d colliders, spans %.0f x %.0f m"
			% [
				MeshContract.triangles(tramway),
				tramway.find_children("*", "StaticBody3D", true, false).size(),
				bounds.size.x,
				bounds.size.z,
			]
		)
	)
