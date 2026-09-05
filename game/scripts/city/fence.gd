## Stands the authored barriers where `fence.json` places them (`P3-29`).
##
## `RoadGraph.fits_car` refuses the edges a car cannot get down, and 🔴 **a
## refusal the player cannot see is the defect it was meant to fix**: round 0 of
## `P3-9a` ended with three HK drivers stopping at geometry they could not read.
## This is what stands where the refusal is.
##
## 🔴 **One MultiMesh for the look, one collision body per unit — never 90
## instanced scenes.** Instantiating the prop per placement is the obvious build
## and it was measured: **+36 draw calls** on a driving frame (92 against 56)
## against `ARCHITECTURE.md`'s <150 budget, on a layer every other generated
## class ships in **one**. A `MultiMesh` draws the 90 units in a single call
## because they share one mesh, and the colliders cost no draw call at all —
## `StaticBody3D` is not a `VisualInstance3D`. `landmarks.gd` instances scenes
## because a hero is unique and there are two of them; neither is true here.
##
## ⚠️ **The collision is the point of this prop and must survive that.** It is
## the only thing in the barrier family that collides — every generated railing
## class is deliberately collider-free (`game/tuning/barriers.tres`) — because a
## barrier the car drives through is `Q19`'s invisible wall with a picture over
## it. The shape is read off the imported `-col` body once and **shared** by
## reference across all 90 bodies, so it is one trimesh in memory either way.
##
## No streaming and no LOD: one draw call and 90 shapes against a 300k triangle
## budget, so residency is cheaper than the machinery. Measure with
## `tools/frame_stats.py` and the driver's own `prims=/draws=` line before
## believing that sentence about a bigger region.
extends Node3D

const GeneratedFence = preload("res://scripts/city/generated_fence.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")
const PropBatch = preload("res://scripts/city/prop_batch.gd")


func _ready() -> void:
	# The manifest is the shipping route (`P1-7`): an exported build cannot
	# enumerate `res://`, so what it does not name does not exist. The locator
	# supplies the schema and the hint; `verify_fence.gd` asserts the two name
	# the same file.
	var manifest: CityManifest = CityManifest.load_manifest()
	if manifest == null:
		return
	var document: Dictionary = GeneratedFence.load_fence(manifest.fence_path)
	if document.is_empty():
		return

	var barriers: Array = document.get("barriers", []) as Array
	if barriers.is_empty():
		# Not an error and not silence: an empty fence is a real state — every
		# edge clears the car — and it has to be distinguishable from a stage
		# that never ran, which is what the locator's hint covers.
		print("fence: nothing to close")
		return

	var asset: String = str(document.get("asset", ""))
	var packed := load(asset) as PackedScene
	if packed == null:
		push_error("fence names %s, which did not load as a scene" % asset)
		return
	var prop: Node3D = packed.instantiate()
	var mesh: Mesh = _mesh_of(prop)
	var shape: Shape3D = _shape_of(prop)
	prop.free()
	if mesh == null:
		push_error("fence prop %s carries no mesh" % asset)
		return
	if shape == null:
		# Refused rather than drawn without collision: a barrier the car passes
		# through is the invisible refusal this layer exists to remove, and it
		# would look completely correct in every frame.
		push_error("fence prop %s imported no collision shape — see the -col suffix" % asset)
		return

	var transforms: Array[Transform3D] = []
	var refused: int = 0
	for entry: Dictionary in barriers:
		var edge_id: int = int(entry.get("edge", -1))
		var node_id: int = int(entry.get("node", -1))
		var placement: Variant = GeneratedFence.placement_of(entry)
		if placement == null:
			# Reported per barrier rather than counted, because the fence is tens
			# of units: a malformed one is a bug in this session's bundle, not a
			# distribution to summarise.
			push_error("barrier on edge %d at node %d has no usable placement" % [edge_id, node_id])
			refused += 1
			continue
		var at: Transform3D = placement as Transform3D
		transforms.append(at)
		add_child(
			_collider(shape, at, "barrier_col_e%d_n%d_%d" % [edge_id, node_id, transforms.size()])
		)

	add_child(PropBatch.batch(mesh, transforms, "BarrierRow"))
	# ⚠️ **Both halves printed, and the collider count with them.** `placed` alone
	# reads as success on a bundle where half the fence was refused, and a fence
	# with holes in it is the state `Q19` forbids shipping. The collider count is
	# here because the MultiMesh split put the *look* and the *collision* in
	# different nodes: `verify_fence.gd` grades the asset's own `-col` import and
	# would stay green if this function stopped building bodies at all, which is a
	# barrier the car drives through and renders perfectly.
	# `layer_preview.gd` prints its collider count for the mirror-image reason.
	print(
		(
			"fence: %d barriers placed at %d mouths, %d refused, %d colliders"
			% [
				transforms.size(),
				int(document.get("mouths", 0)),
				refused,
				MeshContract.colliders(self)
			]
		)
	)


## The prop's mesh, or `null`. Its surface material rides with it, so the
## MultiMesh renders exactly what an instanced scene would have.
func _mesh_of(prop: Node3D) -> Mesh:
	var found: Array[Node] = prop.find_children("*", "MeshInstance3D", true, false)
	if found.is_empty():
		return null
	return (found[0] as MeshInstance3D).mesh


## The shape the `-col` suffix imported, or `null`. Shared by reference across
## every body below rather than duplicated per barrier.
func _shape_of(prop: Node3D) -> Shape3D:
	var found: Array[Node] = prop.find_children("*", "CollisionShape3D", true, false)
	if found.is_empty():
		return null
	return (found[0] as CollisionShape3D).shape


func _collider(shape: Shape3D, at: Transform3D, name_: String) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.name = name_
	body.transform = at
	var collision := CollisionShape3D.new()
	collision.shape = shape
	body.add_child(collision)
	return body
