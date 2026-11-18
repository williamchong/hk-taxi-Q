## Whether a box lies wholly outside a camera's view, the far plane ignored,
## or further from it than a far version is drawn (`P3-100`, `Q249`).
##
## A layer drawn past the far plane (`GeneratedLayer.beyond_far`) carries a
## cull margin the engine cannot cull through, so it was submitted every
## frame from every street, facing the harbour or not. `city_layer.gd` asks
## this instead and hides what the camera cannot see.
extends RefCounted

## `Camera3D.get_frustum`'s order: near, far, left, top, right, bottom.
const FAR_PLANE: int = 1

## How far a box is grown before it is tested, in metres. The answer is a
## frame old when it is used, so a camera swinging round would otherwise show
## the sky for one frame where the far shore is about to be.
const GROW_M: float = 200.0


## True where `box`, grown by `GROW_M`, is wholly beyond one of `planes` other
## than the far one. `planes` face outward, as the engine hands them over.
static func outside(planes: Array[Plane], box: AABB) -> bool:
	var grown: AABB = box.grow(GROW_M)
	for index: int in planes.size():
		if index == FAR_PLANE:
			continue
		var plane: Plane = planes[index]
		# The corner furthest back along the plane's normal: if even that is
		# over the plane, every corner is.
		if plane.is_point_over(grown.get_support(-plane.normal)):
			return true
	return false


## True where every point of `box` is further than `reach_m` from `eye`: the
## camera is outside the box and its nearest point is past the reach.
static func beyond(eye: Vector3, box: AABB, reach_m: float) -> bool:
	var nearest: Vector3 = eye.clamp(box.position, box.end)
	return eye.distance_to(nearest) > reach_m
