## Instantiates the ETL's lamp posts, for looking at the city.
##
## A dev tool, not the streamer, exactly like `railings_preview.gd`. The whole
## region's columns are one mesh — ~35.9k triangles for Wan Chai over 897 posts —
## so there is nothing to stream, and deliberately nothing to LOD: `Q34`'s vertex
## clustering annihilates anything thinner than a cell, and a 90 mm column is
## exactly that.
##
## No transform is applied, for the same reason as the road surface, the arrows
## and the road markings: `lamps.py` writes vertices in **region** game space, so
## a node at the origin already lines up with the kerb it stands on.
##
## 🔴 **This node existing at all is `Q73`, and it took TWO commits when it
## should have taken one.** `roadmarks.glb` was built, exported, synced,
## imported, graded by its own verify tool and drawn *nowhere* — `check.sh`
## green throughout, because a verify tool asks "is this asset correct" and never
## "is this asset on screen".
##
## 🔴 **This file then repeated it while quoting it.** The node went into
## `city_preview.tscn` and not `city_drive.tscn`, which is the scene the game
## boots into; the layer was correct, verified, visible in every preview shot and
## **absent from the game**, until someone drove it and asked where the poles
## were. **A drawn layer needs a node in BOTH scenes, in the same commit as the
## asset** — and nothing but looking will tell you it does not.
##
## ⚠️ **Absence is not a warning here.** A city whose estate publishes no utility
## point layer ships none (`P3-26`), so a missing asset prints what happened and
## returns.
extends Node3D

const GeneratedLamps = preload("res://scripts/city/generated_lamps.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")


func _ready() -> void:
	# 🔴 **`is_present()`, never a null check on `load_lamps()`.** They answer
	# different questions and only one of them is quiet: `load()` on an absent
	# path writes `ERROR: No loader found for resource` to the console *before*
	# it returns null, so a graceful branch below it runs after the damage is
	# done. `Q77` dropped the signal layer and that error then shipped in the web
	# build — into the console `P3-9a` tells testers to read, under a row
	# claiming 0 errors. Do not "simplify" it back to one check.
	if not GeneratedLamps.is_present():
		print("lamps: none shipped for this region")
		return

	var packed: PackedScene = GeneratedLamps.load_lamps()
	if packed == null:
		# Present but unloadable, which is not the same as absent — reporting it
		# as "none shipped" would describe a broken asset as an empty region.
		push_error("lamps: %s exists but did not load as a scene" % GeneratedLamps.PATH)
		return

	var lamps: Node3D = packed.instantiate()
	lamps.name = "Lamps"
	add_child(lamps)

	var bounds: AABB = MeshContract.bounds(lamps)

	# Colliders are printed because there must be **none**. A lamp column is a
	# 90 mm prism standing every twenty metres down every kerb in the city, so
	# modelling 897 of them as collision geometry before `P2-6` has measured a
	# frame on the device floor is the wrong order — and a car catching one
	# mid-drift is a worse failure than a car passing through it. `B3` revisits
	# it; breakaway poles are the genre's answer, and that is an effect rather
	# than a shape.
	print(
		(
			"lamps: %d triangles, %d colliders, spans %.0f x %.0f m, %.1f m tall"
			% [
				MeshContract.triangles(lamps),
				lamps.find_children("*", "StaticBody3D", true, false).size(),
				bounds.size.x,
				bounds.size.z,
				bounds.size.y,
			]
		)
	)
