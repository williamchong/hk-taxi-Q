## Instantiates the ETL's pedestrian railings, for looking at the city.
##
## A dev tool, not the streamer, exactly like `boxjunctions_preview.gd`. The
## whole region's railings are one mesh — ~9k triangles for Wan Chai over 9 km
## of fence — so there is nothing to stream, and deliberately nothing to LOD:
## `Q34`'s vertex clustering annihilates anything thinner than a cell, and a
## fence is a surface 40 mm thick.
##
## No transform is applied, for the same reason as the road surface, the arrows
## and the box junctions: `railings.py` writes vertices in **region** game
## space, so a node at the origin already stands on the kerb it was joined to.
##
## ⚠️ **Absence is not a warning here.** A city whose estate publishes no railing
## layer ships none (`P3-19`), so a missing asset prints what happened and
## returns.
extends Node3D

const GeneratedRailings = preload("res://scripts/city/generated_railings.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")


func _ready() -> void:
	# `is_present()` before `load()`, and `signals_preview.gd` carries the reason:
	# `load()` on an absent path errors into the console before it returns null,
	# so a null check alone is graceful only after the damage (`Q77`). Latent while
	# this layer ships; a second city is what makes it live.
	if not GeneratedRailings.is_present():
		print("railings: none shipped for this region")
		return

	var packed: PackedScene = GeneratedRailings.load_railings()
	if packed == null:
		# Present but unloadable, which is not the same as absent.
		push_error("railings: %s exists but did not load as a scene" % GeneratedRailings.PATH)
		return

	var fences: Node3D = packed.instantiate()
	fences.name = "Railings"
	add_child(fences)

	var bounds: AABB = MeshContract.bounds(fences)

	# Colliders are printed because there must be **none**, and here that is a
	# design decision rather than a rendering one: `GAME_DESIGN.md` lists
	# railings under "omit or make breakable" precisely because a solid one
	# turns a narrow street into a corridor. Collision is a `B3` question.
	print(
		(
			"railings: %d triangles, %d colliders, spans %.0f x %.0f m, %.1f m tall"
			% [
				MeshContract.triangles(fences),
				fences.find_children("*", "StaticBody3D", true, false).size(),
				bounds.size.x,
				bounds.size.z,
				bounds.size.y,
			]
		)
	)
