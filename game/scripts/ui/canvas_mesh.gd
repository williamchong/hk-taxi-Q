class_name CanvasMesh
extends RefCounted
## A vertex-coloured triangle mesh for a canvas item — the block the minimap,
## the dial and the meter's digits each wrote out (`P3-44`). One mesh is one
## draw call where a polygon a shape is one each; see `minimap_mesh.gd`.


## `vertices` as unindexed triangles, a colour a vertex.
static func of(vertices: PackedVector2Array, colours: PackedColorArray) -> ArrayMesh:
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_COLOR] = colours
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh
