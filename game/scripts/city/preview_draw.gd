## Drawing shared by the dev previews.
##
## Two things every diagram in `scenes/dev/` needs: a flat ribbon laid between
## two points, and a material that shows vertex colour as itself. Both were
## written twice before this existed — `road_preview.gd` drawing edges and
## `fare_preview.gd` drawing tethers — and the ribbon's winding order is exactly
## the kind of detail that gets fixed in one copy and not the other.
##
## Previews only. `P1-4` builds the real road surface in the ETL, with mitred
## joints and closed corners; nothing here is trying to be that.
extends RefCounted


## One flat quad in the XZ plane, from `from` to `to`.
##
## Unmitred: consecutive quads overlap slightly on the inside of a bend and
## leave a wedge on the outside. Wrong for a road surface, fine for a diagram.
##
## Returns false if the two points are too close to give a direction, so a
## caller can tell "nothing drawn" from "drawn" without measuring again.
static func ribbon(
	surface: SurfaceTool, from: Vector3, to: Vector3, half_width: float, colour: Color
) -> bool:
	var along := to - from
	along.y = 0.0
	if along.length_squared() < 1e-8:
		# A zero-length quad is two degenerate triangles in the mesh.
		return false
	var side: Vector3 = along.normalized().cross(Vector3.UP) * half_width

	surface.set_color(colour)
	for corner: Vector3 in [from - side, from + side, to + side, from - side, to + side, to - side]:
		surface.add_vertex(corner)
	return true


## Unshaded, vertex-coloured, double-sided.
##
## Unshaded so the colours read as the categories they encode rather than as
## whatever the sun is doing to them. Double-sided because every preview draws
## single-sided quads that get looked at from below — under a flyover, or up at
## a marker from the driver's seat.
static func unshaded_material() -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.vertex_color_use_as_albedo = true
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	return material
