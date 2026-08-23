## Instantiates the ETL's stop and give-way lines, for looking at the city.
##
## A dev tool, not the streamer, exactly like `boxjunctions_preview.gd`. The
## whole region's bars are one mesh — ~4.5k triangles for Wan Chai over 191
## markings — so there is nothing to stream, and deliberately nothing to LOD:
## `Q34`'s vertex clustering annihilates anything thinner than a cell, and a
## 200 mm stop line is exactly that.
##
## No transform is applied, for the same reason as the road surface and the
## arrows: `roadmarks.py` writes vertices in **region** game space, so a node at
## the origin already lines up with the junction mouth it is painted across.
##
## A separate mesh rather than paint on the ribbon, which is `arrows.py`'s
## argument in its strongest form: a stop line lives *at* the junction, on the
## cap, inside `road_markings.tres`'s 6 m fade — so drawing it on the surface
## would blank it at exactly the junctions it is about.
##
## ⚠️ **Absence is not a warning here.** A city whose estate publishes no
## transverse markings ships none (`P3-23`), so a missing asset prints what
## happened and returns.
extends Node3D

const GeneratedRoadMarks = preload("res://scripts/city/generated_roadmarks.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")


func _ready() -> void:
	var packed: PackedScene = GeneratedRoadMarks.load_roadmarks()
	if packed == null:
		print("roadmarks: none shipped for this region")
		return

	var marks: Node3D = packed.instantiate()
	marks.name = "RoadMarks"
	add_child(marks)

	var bounds: AABB = MeshContract.bounds(marks)

	# Colliders are printed because there must be **none**, and this layer is
	# the sharpest case for it: a stop line crosses every approach in the city,
	# so a 16 mm step modelled as collision geometry is a kerb the player mounts
	# at every junction while braking.
	print(
		(
			"roadmarks: %d triangles, %d colliders, spans %.0f x %.0f m"
			% [
				MeshContract.triangles(marks),
				marks.find_children("*", "StaticBody3D", true, false).size(),
				bounds.size.x,
				bounds.size.z,
			]
		)
	)
