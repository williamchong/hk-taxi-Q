class_name PlanLattice
extends RefCounted
## An even grid of plan positions over a region, for sweeping a query.
##
## Two verify tools sweep the region asking "what does this system say *here*",
## and both need the same points: `verify_road_graph.gd` times `nearest_edge`
## against them and `verify_city_streamer.gd` counts what the streamer would
## make resident. They were written twice before this existed, which is the same
## reason `preview_draw.gd` and `mesh_contract.gd` exist.
##
## Pure and `Node`-free, per the `scripts/core/` rule in docs/ARCHITECTURE.md.

const MIN_SPACING_M: float = 0.01


## Positions spaced `spacing_m` apart across `bounds`, at `y = 0`.
##
## Height is dropped because every distance either tool measures is plan
## distance — `RoadGraph` because a car sits a ride height above the road it is
## matched to, `TileStreaming` because a tile's AABB spans ground to roof and a
## street-level camera is inside that range anyway.
##
## Counted rather than accumulated. Stepping a float across the span drops the
## last row or column whenever the spacing does not divide the extent exactly,
## which silently shrinks the sweep at the region's far edge — the two corners a
## streamer or an index is most likely to get wrong.
##
## `bounds` should be the manifest's, which is the union of the region's content
## and larger than its declared rectangle: tiles overhang and the road ribbon is
## drawn outward from centrelines that run to the boundary.
static func over(bounds: AABB, spacing_m: float) -> PackedVector3Array:
	var step: float = maxf(spacing_m, MIN_SPACING_M)
	var points := PackedVector3Array()
	var columns: int = maxi(1, int(bounds.size.x / step))
	var rows: int = maxi(1, int(bounds.size.z / step))
	points.resize((rows + 1) * (columns + 1))
	var at: int = 0
	for row: int in rows + 1:
		for column: int in columns + 1:
			points[at] = Vector3(
				bounds.position.x + float(column) * step,
				0.0,
				bounds.position.z + float(row) * step,
			)
			at += 1
	return points
