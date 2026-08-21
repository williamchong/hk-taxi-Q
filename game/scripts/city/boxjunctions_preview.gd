## Instantiates the ETL's yellow box junctions, for looking at the city.
##
## A dev tool, not the streamer, exactly like `arrows_preview.gd`. The whole
## region's boxes are one mesh — ~12k triangles for Wan Chai over 20 junctions —
## so there is nothing to stream, and deliberately nothing to LOD: `Q34`'s
## vertex clustering annihilates anything thinner than a cell, and a 100 mm
## hatch line is exactly that.
##
## No transform is applied, for the same reason as the road surface and the
## arrows: `boxjunctions.py` writes vertices in **region** game space, so a node
## at the origin already lines up with the junction it is painted on.
##
## ⚠️ **Absence is not a warning here.** A city whose estate publishes no box
## polygons ships none (`P3-18`), so a missing asset prints what happened and
## returns.
extends Node3D

const GeneratedBoxJunctions = preload("res://scripts/city/generated_boxjunctions.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")


func _ready() -> void:
	var packed: PackedScene = GeneratedBoxJunctions.load_boxjunctions()
	if packed == null:
		print("boxjunctions: none shipped for this region")
		return

	var boxes: Node3D = packed.instantiate()
	boxes.name = "BoxJunctions"
	add_child(boxes)

	var bounds: AABB = MeshContract.bounds(boxes)

	# Colliders are printed because there must be **none**, for the reason
	# `arrows_preview.gd` gives: the hatch lies across the middle of every boxed
	# junction, so a collider is a 12 mm step every vehicle crosses at speed.
	print(
		(
			"boxjunctions: %d triangles, %d colliders, spans %.0f x %.0f m"
			% [
				MeshContract.triangles(boxes),
				boxes.find_children("*", "StaticBody3D", true, false).size(),
				bounds.size.x,
				bounds.size.z,
			]
		)
	)
