## The pool of light under every lamp post (`Q160`): one cylinder of air per
## lantern, drawn by `lamp_pool.gdshader`, which lights what stands inside it.
## The shader's header says why this is not a light.
##
## Static, and `layer_preview.gd` is the one caller: it already has the
## library's meshes and where each stands, and the pools ride the lamps' own
## plan cells so a street of them is one draw.
extends RefCounted

## The pools' material: the look, and the cylinder's two dimensions.
const MATERIAL_PATH: String = "res://tuning/lamp_pools.tres"

## The ETL's mark on a lantern's luminous faces — `COLOR_0` alpha 0, against
## 255 everywhere else (`etl/pipeline/lamps.py::LANTERN_LIT_ALPHA`).
const LIT_BELOW_ALPHA: float = 0.5

## Flat sides to a pool's cylinder.
const SIDES: int = 12


## Where a library column's lantern hangs, in the column's own frame: the
## centre of its marked vertices. `Vector3.INF` for a mesh that marks none —
## a bundle from before the mark, which `verify_lamps.gd` refuses.
static func lantern_of(mesh: Mesh) -> Vector3:
	var box := AABB()
	var found: bool = false
	for surface: int in mesh.get_surface_count():
		var arrays: Array = mesh.surface_get_arrays(surface)
		var positions: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var colours: Variant = arrays[Mesh.ARRAY_COLOR]
		if not colours is PackedColorArray:
			continue
		var marks: PackedColorArray = colours
		for index: int in marks.size():
			if marks[index].a >= LIT_BELOW_ALPHA:
				continue
			box = box.expand(positions[index]) if found else AABB(positions[index], Vector3.ZERO)
			found = true
	return box.get_center() if found else Vector3.INF


## The cylinder one pool draws, sized by the material: `radius_m` round and
## `drop_m` tall, its top centre the lantern.
static func cylinder(material: ShaderMaterial) -> CylinderMesh:
	var mesh := CylinderMesh.new()
	var radius: float = material.get_shader_parameter(&"radius_m")
	# Flat sides inscribe the circle; this circumscribes it again.
	mesh.top_radius = radius / cos(PI / SIDES)
	mesh.bottom_radius = mesh.top_radius
	mesh.height = material.get_shader_parameter(&"drop_m")
	mesh.radial_segments = SIDES
	mesh.rings = 0
	mesh.material = material
	return mesh


## Each column's transform moved to its pool's: the cylinder's centre, half a
## drop under the lantern.
static func stand(
	columns: Array[Transform3D], lantern: Vector3, drop_m: float
) -> Array[Transform3D]:
	var pools: Array[Transform3D] = []
	var centre: Vector3 = lantern - Vector3(0.0, drop_m * 0.5, 0.0)
	for column: Transform3D in columns:
		pools.append(Transform3D(Basis.IDENTITY, column * centre))
	return pools
