class_name TileStreaming
extends RefCounted
## Which tier a tile should be at, given where the camera is (`P2-1`).
##
## The policy half of `CityStreamer`, and pure on purpose: no `Node`, no
## `load()`, no rendering calls, per the `scripts/core/` rule in
## docs/ARCHITECTURE.md. Everything here is a function of a distance and a
## profile, so `tools/verify_city_streamer.gd` can assert the whole decision
## table headlessly without a scene, a camera or a built city.
##
## That split is also what makes `P2-1`'s third acceptance criterion — "a
## distant tile is rejected by its `aabb` **before** its mesh is loaded" — a
## structural property rather than a promise. Deciding takes an `AABB` and
## returns an int; there is no code path from here to a file.

## Tier value meaning "this tile should not be resident at all".
const UNLOADED: int = -1


## Plan distance from `point` to the nearest part of `box`, and 0 inside it.
##
## Plan, not 3D, for the same reason `RoadGraph` measures in plan — but here the
## two are usually the same number. A tile's AABB spans from the ground to its
## tallest roof, so a camera at street level sits *inside* the box's vertical
## range and the nearest point on it is at the camera's own height. They diverge
## only for a camera above every roof, which is `city_preview.tscn`'s fly camera
## — and that scene uses `tile_preview.gd`, which loads everything and streams
## nothing. Plan keeps this honest if that ever changes: a camera 500 m up
## should not be told it is 0 m from the block it is over.
static func plan_distance_to(box: AABB, point: Vector3) -> float:
	var end: Vector3 = box.end
	var dx: float = maxf(maxf(box.position.x - point.x, point.x - end.x), 0.0)
	var dz: float = maxf(maxf(box.position.z - point.z, point.z - end.z), 0.0)
	return Vector2(dx, dz).length()


## The tier `distance_m` falls in, ignoring hysteresis.
##
## Returns `UNLOADED` past the unload distance, and `edges.size()` for anything
## beyond the last edge — the coarsest tier. That can exceed the tiers a given
## tile actually has, which is deliberate: `CityManifest.Tile.lod` clamps to
## what the tile carries, because a tile whose geometry survived decimation
## intact stops emitting new tiers and should still draw.
static func band_of(distance_m: float, profile: StreamingProfile) -> int:
	if distance_m > profile.unload_distance_m:
		return UNLOADED
	for tier: int in profile.tier_distances_m.size():
		if distance_m <= profile.tier_distances_m[tier]:
			return tier
	return profile.tier_distances_m.size()


## The tier a tile at `distance_m` should be at, given the tier it is at now.
##
## `current_tier` is `UNLOADED` for a tile that is not resident, and that case
## takes no hysteresis: there is nothing to thrash against yet, and widening the
## band for a tile that does not exist would load it early on one side and late
## on the other.
##
## For a resident tile the band it already occupies is widened by
## `hysteresis_m` on both sides and it stays put while it remains inside. Only
## when it leaves the widened band does the tier get recomputed — from the
## *unwidened* bands, so it lands where a fresh decision would put it rather
## than one margin deep into the next tier along.
static func tier_for(distance_m: float, current_tier: int, profile: StreamingProfile) -> int:
	if current_tier == UNLOADED:
		return band_of(distance_m, profile)

	var edges: PackedFloat32Array = profile.tier_distances_m
	var margin: float = profile.hysteresis_m
	# Clamped because this is a public entry point and `current_tier` comes from
	# a caller's own bookkeeping. An out-of-range tier is a wrong answer worth
	# recovering from; an out-of-range read is a crash.
	var tier: int = clampi(current_tier, 0, edges.size())
	# A tier past the last edge is the coarsest band, whose outer edge is the
	# unload distance rather than an entry in the table.
	var inner: float = (edges[tier - 1] - margin) if tier > 0 else -INF
	var outer: float = (
		(edges[tier] + margin) if tier < edges.size() else profile.unload_distance_m + margin
	)
	if distance_m > inner and distance_m <= outer:
		return tier
	return band_of(distance_m, profile)


## Furthest a tile can be and still be resident, hysteresis included.
##
## `unload_distance_m` is where a *fresh* decision drops a tile; a tile already
## resident keeps its band for another `hysteresis_m`. Anything sizing itself on
## "what the streamer holds" — the residency sweep in `verify_city_streamer.gd`
## — must use this and not the profile field, or it measures a smaller city than
## the streamer actually keeps.
static func residency_radius_m(profile: StreamingProfile) -> float:
	return profile.unload_distance_m + profile.hysteresis_m


## True where the profile describes a city that can actually be streamed.
##
## Checked rather than trusted because an unassigned `StreamingProfile` reads as
## all-zeroes, which is a valid-looking policy that unloads everything: every
## distance exceeds an `unload_distance_m` of 0. The streamer refuses to run on
## one instead of clearing the city and reporting nothing.
static func is_usable(profile: StreamingProfile) -> bool:
	if profile == null or profile.tier_distances_m.is_empty():
		return false
	if profile.unload_distance_m <= 0.0 or profile.max_instantiations_per_frame < 1:
		return false
	if profile.max_loads_in_flight < 1:
		return false
	var previous: float = 0.0
	for edge: float in profile.tier_distances_m:
		# Ascending, and strictly *inside* the unload distance. `>=` rather than
		# `>` because the coarsest tier occupies the span between the last edge
		# and the unload distance: a last edge sitting exactly on it leaves that
		# tier zero-width, so the tile list carries a tier nothing can ever be in.
		if edge <= previous or edge >= profile.unload_distance_m:
			return false
		previous = edge
	return true
