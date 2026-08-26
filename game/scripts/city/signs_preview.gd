## Instantiates the ETL's traffic signs, for looking at the city.
##
## A dev tool, not the streamer, exactly like `railings_preview.gd`. The whole
## region's signage is one mesh — ~19k triangles for Wan Chai over 450 posts — so
## there is nothing to stream, and deliberately nothing to LOD: `Q34`'s vertex
## clustering annihilates anything thinner than a cell, and a sign plate is a
## surface a few millimetres thick on a 64 mm post.
##
## No transform is applied, for the same reason as the road surface, the arrows,
## the box junctions and the railings: `signs.py` writes vertices in **region**
## game space, so a node at the origin already stands on the pole it was joined
## to.
##
## ⚠️ **Absence is not a warning here, and it is the least surprising absence in
## the scene.** `P3-16` draws only the signs whose meaning is their *shape*, and
## 2,364 of Wan Chai's 3,276 are text-faced and refused under `Q42`. A region
## whose signs are all time plates ships none, so a missing asset prints what
## happened and returns.
extends Node3D

const GeneratedSigns = preload("res://scripts/city/generated_signs.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")


func _ready() -> void:
	# `is_present()` before `load()`, and `signals_preview.gd` carries the reason:
	# `load()` on an absent path errors into the console before it returns null,
	# so a null check alone is graceful only after the damage (`Q77`). Latent while
	# this layer ships; a second city is what makes it live.
	if not GeneratedSigns.is_present():
		print("signs: none shipped for this region")
		return

	var packed: PackedScene = GeneratedSigns.load_signs()
	if packed == null:
		# Present but unloadable, which is not the same as absent.
		push_error("signs: %s exists but did not load as a scene" % GeneratedSigns.PATH)
		return

	var posts: Node3D = packed.instantiate()
	posts.name = "Signs"
	add_child(posts)

	var bounds: AABB = MeshContract.bounds(posts)

	# Colliders are printed because there must be **none**, and unlike the
	# railings that is a budget decision rather than a design one: a sign post is
	# a real obstacle a real car would hit. 699 of them is 699 collision bodies,
	# and `P2-6` has not measured a frame on the device floor yet. Breakaway
	# posts are a `B3` question.
	print(
		(
			"signs: %d triangles, %d colliders, spans %.0f x %.0f m, tops out %.1f m"
			% [
				MeshContract.triangles(posts),
				posts.find_children("*", "StaticBody3D", true, false).size(),
				bounds.size.x,
				bounds.size.z,
				bounds.position.y + bounds.size.y,
			]
		)
	)
