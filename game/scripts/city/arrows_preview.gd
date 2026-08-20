## Instantiates the ETL's turn arrows, for looking at the city.
##
## A dev tool, not the streamer, exactly like `tramway_preview.gd`. The whole
## region's arrows are one mesh — ~3k triangles for Wan Chai, against 28k for
## the carriageway they lie on — so there is nothing to stream and nothing to
## LOD.
##
## No transform is applied, for the same reason as the road surface and the
## tramway: `arrows.py` writes vertices in **region** game space, so a node at
## the origin already lines up with the ribbon it is painted on. That alignment
## is load-bearing here in a way it is not for the tramway — an arrow offset by
## a metre sits across a lane divider rather than between two.
##
## ⚠️ **Absence is not a warning here.** A city whose estate publishes no marking
## symbols ships none (`P3-15`), so a missing asset prints what happened and
## returns.
extends Node3D

const GeneratedArrows = preload("res://scripts/city/generated_arrows.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")


func _ready() -> void:
	var packed: PackedScene = GeneratedArrows.load_arrows()
	if packed == null:
		print("arrows: none shipped for this region")
		return

	var arrows: Node3D = packed.instantiate()
	arrows.name = "Arrows"
	add_child(arrows)

	var bounds: AABB = MeshContract.bounds(arrows)

	# Colliders are printed because there must be **none**, the same reason
	# `tramway_preview.gd` prints them and a sharper one: an arrow lies flat
	# across a lane the car drives along, so a collider is a step every vehicle
	# in the region crosses at speed rather than one at the edge of the road.
	print(
		(
			"arrows: %d triangles, %d colliders, spans %.0f x %.0f m"
			% [
				MeshContract.triangles(arrows),
				arrows.find_children("*", "StaticBody3D", true, false).size(),
				bounds.size.x,
				bounds.size.z,
			]
		)
	)
