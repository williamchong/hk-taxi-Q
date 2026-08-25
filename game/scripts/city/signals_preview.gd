## Instantiates the ETL's traffic signal heads, for looking at the city.
##
## A dev tool, not the streamer, exactly like `roadmarks_preview.gd`. The whole
## region's heads are one mesh — ~37.7k triangles for Wan Chai over 681 aspects
## on 415 posts — so there is nothing to stream, and deliberately nothing to
## LOD: `Q34`'s vertex clustering annihilates anything thinner than a cell, and a
## 60 mm post is exactly that.
##
## No transform is applied, for the same reason as the road surface, the arrows
## and the road markings: `signals.py` writes vertices in **region** game space,
## so a node at the origin already lines up with the junction it stands at.
##
## 🔴 **This node existing at all is `Q73`.** `roadmarks.glb` was built,
## exported, synced, imported, graded by its own verify tool and drawn *nowhere*
## — and `check.sh` was green throughout, because a verify tool asks "is this
## asset correct" and never "is this asset on screen". Every layer here has that
## blind spot, so the node ships in the same commit as the asset.
##
## ⚠️ **Absence is not a warning here.** A city whose estate publishes no signal
## layer ships none (`P3-17`), and so does one whose publisher spells its codes
## differently — the gate is a rule about spelling that nothing published grades.
## So a missing asset prints what happened and returns.
extends Node3D

const GeneratedSignals = preload("res://scripts/city/generated_signals.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")


func _ready() -> void:
	var packed: PackedScene = GeneratedSignals.load_signals()
	if packed == null:
		print("signals: none shipped for this region")
		return

	var signals: Node3D = packed.instantiate()
	signals.name = "Signals"
	add_child(signals)

	var bounds: AABB = MeshContract.bounds(signals)

	# Colliders are printed because there must be **none**. A signal post is a
	# 60 mm prism standing at every junction mouth in the city, so modelling it
	# as collision geometry before `P2-6` has measured a frame on the device
	# floor is the wrong order — and a car catching one mid-drift is a worse
	# failure than a car passing through it. `B3` revisits it; breakaway poles
	# are the genre's answer, and that is an effect rather than a shape.
	print(
		(
			"signals: %d triangles, %d colliders, spans %.0f x %.0f m"
			% [
				MeshContract.triangles(signals),
				signals.find_children("*", "StaticBody3D", true, false).size(),
				bounds.size.x,
				bounds.size.z,
			]
		)
	)
