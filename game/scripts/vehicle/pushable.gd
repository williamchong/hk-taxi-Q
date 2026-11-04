class_name Pushable
extends RefCounted
## A body the taxi pushes by momentum (`Q180`): a moving car or a tram. Its owner
## marks it, and `VehicleController._integrate_forces` exchanges momentum with it
## along the contact, off the two masses and `collision_restitution`, where an
## unmarked body is a wall of infinite mass as before.
##
## The owner answers two calls, both in world space:
##   `push_inverse_mass(body, normal, at) -> float` — how readily the body gives
##       along `normal` at the contact point `at`: `1 / m` and a box's turn for a
##       car, `(normal · rails)² / m` for a tram, which cannot leave its rails.
##   `take_push(body, impulse, at)` — the impulse the taxi put into it there.
##
## `--push=off` marks nothing: every body is a wall again, byte for byte.

const ARG: String = "--push="
const OWNER_META: StringName = &"pushed_by"


## Mark `body` as `owner`'s to push, unless the run turned pushing off.
static func mark(body: CollisionObject3D, owner: Object) -> void:
	if Cmdline.off(ARG):
		return
	body.set_meta(OWNER_META, owner)


## Who pushes `collider`, or null for a wall.
static func owner_of(collider: Object) -> Object:
	if collider == null or not collider.has_meta(OWNER_META):
		return null
	return collider.get_meta(OWNER_META)


## A box's moment of inertia about the vertical, in kg·m²: `m (l² + w²) / 12`.
static func yaw_inertia(mass_kg: float, half_length: float, half_width: float) -> float:
	return mass_kg * (4.0 * half_length * half_length + 4.0 * half_width * half_width) / 12.0


## The vertical part of `arm × force` in plan: what turns a box about its centre.
static func yaw_moment(arm: Vector3, force: Vector3) -> float:
	return arm.z * force.x - arm.x * force.z


## How readily a free box of `mass_kg` centred at `centre` gives along `normal`
## at `at`, in plan: its mass and the turn an off-centre push buys.
static func box_inverse_mass(
	mass_kg: float,
	half_length: float,
	half_width: float,
	centre: Vector3,
	normal: Vector3,
	at: Vector3
) -> float:
	var arm := Vector3(at.x - centre.x, 0.0, at.z - centre.z)
	var turn: float = yaw_moment(arm, Vector3(normal.x, 0.0, normal.z))
	return 1.0 / mass_kg + turn * turn / yaw_inertia(mass_kg, half_length, half_width)


## How readily a body of `mass_kg` held to `rails` gives along `normal`, in plan:
## only the part along its rails, so square across them it does not give at all.
static func rails_inverse_mass(mass_kg: float, rails: Vector3, normal: Vector3) -> float:
	var share: float = normal.x * rails.x + normal.z * rails.z
	return share * share / mass_kg
