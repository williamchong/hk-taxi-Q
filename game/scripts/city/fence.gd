## Stands the authored barriers where `fence.json` places them (`P3-29`).
##
## `RoadGraph.fits_car` refuses the edges a car cannot get down, and 🔴 **a
## refusal the player cannot see is the defect it was meant to fix**: round 0 of
## `P3-9a` ended with three HK drivers stopping at geometry they could not read.
## This is what stands where the refusal is.
##
## 🔴 **One MultiMesh for the look, one collision body per unit — never an
## instanced scene per unit.** Instantiating the prop per placement is the obvious build
## and it was measured: **+36 draw calls** on a driving frame (92 against 56)
## against `ARCHITECTURE.md`'s <150 budget, on a layer every other generated
## class ships in **one**. A `MultiMesh` draws every unit in a single call
## because they share one mesh, and the colliders cost no draw call at all —
## `StaticBody3D` is not a `VisualInstance3D`. `landmarks.gd` instances scenes
## because a hero is unique and there are two of them; neither is true here.
##
## ⚠️ **The collision is the point of this prop and must survive that** —
## because a barrier the car drives through is `Q19`'s invisible wall with a
## picture over it. The generated railing classes collide too since `Q159`,
## through their placer's `collides` switch; their asset stays collider-free
## (`verify_railings.gd`). The extent is read off the imported `-col` body once
## and stood as one **box**, shared by every body. ⚠️ **A box, not the
## trimesh `-col` imports**: that is the rails and posts face for face, so a
## bumper meets open air under the 0.34 m bottom rail and between the two
## courses and snags on a rail edge, where a closure should stop the car flat.
##
## No streaming and no LOD: one draw call and a box per unit against a 300k triangle
## budget, so residency is cheaper than the machinery. Measure with
## `tools/frame_stats.py` and the driver's own `prims=/draws=` line before
## believing that sentence about a bigger region.
extends Node3D

const GeneratedFence = preload("res://scripts/city/generated_fence.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")
const PropBatch = preload("res://scripts/city/prop_batch.gd")

## Which synced region's barriers; "" is `GeneratedRegions.selected()`. Set by
## `CityRegions` before the node enters the tree (`P5-9c`).
@export var region: String = ""


func _ready() -> void:
	# The manifest is the shipping route (`P1-7`): an exported build cannot
	# enumerate `res://`, so what it does not name does not exist. The locator
	# supplies the schema and the hint; `verify_fence.gd` asserts the two name
	# the same file.
	var manifest: CityManifest = CityManifest.shared(region)
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
	var extent: AABB = _extent_of(prop)
	prop.free()
	if mesh == null:
		push_error("fence prop %s carries no mesh" % asset)
		return
	if not extent.has_volume():
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

	for body: StaticBody3D in PropBatch.bodies(extent, transforms, "barrier_col"):
		add_child(body)
	add_child(PropBatch.batch(mesh, transforms, "BarrierRow"))
	# ⚠️ **Both halves printed, and the collider count with them.** `placed` alone
	# reads as success on a bundle where half the fence was refused, and a fence
	# with holes in it is the state `Q19` forbids shipping. The collider count is
	# here because the MultiMesh split put the *look* and the *collision* in
	# different nodes: `verify_fence.gd` grades the asset's own `-col` import and
	# would stay green if this function stopped building bodies at all, which is a
	# barrier the car drives through and renders perfectly.
	# `layer_preview.gd` prints its count too: none but the railings may have any.
	print(
		(
			"fence: %d barriers placed at %d mouths and %d clipped ends, %d refused, %d colliders"
			% [
				transforms.size(),
				int(document.get("mouths", 0)),
				int(document.get("clipped_ends", 0)),
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


## The extent of the shape the `-col` suffix imported, in the prop's frame, or
## an empty `AABB` when it imported none. The `-col` stays the source of the
## box, so the asset still decides where the barrier is solid and a prop
## without one is still refused.
func _extent_of(prop: Node3D) -> AABB:
	var found: Array[Node] = prop.find_children("*", "CollisionShape3D", true, false)
	if found.is_empty():
		return AABB()
	var imported := found[0] as CollisionShape3D
	# Up to the prop's root, which is where the MultiMesh and the bodies stand.
	var to_root: Transform3D = imported.transform
	var parent: Node = imported.get_parent()
	while parent != null and parent != prop:
		to_root = (parent as Node3D).transform * to_root
		parent = parent.get_parent()
	return to_root * imported.shape.get_debug_mesh().get_aabb()
