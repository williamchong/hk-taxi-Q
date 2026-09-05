## One `MultiMesh` over many transforms — how a repeated prop draws in one call.
##
## `fence.gd` measured the alternative: the barrier instantiated as a scene per
## placement cost **+36 draw calls** on a driving frame against a `MultiMesh`'s
## +1, pixel-identical (`P3-29`). `P5-2` made it the shape every prop layer
## takes — a sign library, and the lamps and arrows after it (`Q115`) — so the
## idiom lives here once rather than once per placer.
extends RefCounted


## `transforms.size()` copies of `mesh`, as one node.
static func batch(mesh: Mesh, transforms: Array[Transform3D], name: String) -> MultiMeshInstance3D:
	var multi := MultiMesh.new()
	multi.transform_format = MultiMesh.TRANSFORM_3D
	multi.mesh = mesh
	# Set after `mesh` and `transform_format`: `instance_count` allocates the
	# buffer, so assigning it first and the format second discards every
	# transform written in between.
	multi.instance_count = transforms.size()
	for index: int in transforms.size():
		multi.set_instance_transform(index, transforms[index])
	var node := MultiMeshInstance3D.new()
	node.name = name
	node.multimesh = multi
	return node
