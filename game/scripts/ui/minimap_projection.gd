class_name MinimapProjection
extends RefCounted
## Where the city lands on the minimap (`P3-44`) — pure arithmetic, so
## `verify_hud.gd` can grade it without a frame.
##
## Game `-Z` is north and `+X` is east (`CityManifest.bearing_deg`); a canvas has
## `+Y` down. So plan `(x, z)` IS canvas `(x, y)` with north up — no flip — and
## the only place a mirrored map can come from is the sign of the heading
## rotation below. ⚠️ A mirrored map of a street grid looks entirely plausible,
## which is why east-is-right is asserted rather than looked at.


## A world position in the map mesh's own space: plan metres.
static func plan(world: Vector3) -> Vector2:
	return Vector2(world.x, world.z)


## The transform that carries plan metres onto the slot, with `car` on
## `anchor_px`.
##
## The bearing is `CityManifest.bearing_deg`'s and never a second convention:
## clockwise from north, and a positive canvas rotation is clockwise too (`+Y`
## is down), so turning the map by MINUS the bearing is what brings the nose up.
static func roads_transform(
	car: Vector3, forward: Vector3, heading_up: bool, px_per_m: float, anchor_px: Vector2
) -> Transform2D:
	var turn: float = -deg_to_rad(CityManifest.bearing_deg(forward)) if heading_up else 0.0
	var placed := Transform2D(turn, Vector2(px_per_m, px_per_m), 0.0, Vector2.ZERO)
	placed.origin = anchor_px - placed.basis_xform(plan(car))
	return placed


## How far the car's chevron is turned. It points up under `heading_up` — the
## map turns instead — and along the bearing with north pinned.
static func marker_rotation(forward: Vector3, heading_up: bool) -> float:
	return 0.0 if heading_up else deg_to_rad(CityManifest.bearing_deg(forward))
