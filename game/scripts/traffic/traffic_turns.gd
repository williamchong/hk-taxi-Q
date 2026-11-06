class_name TrafficTurns
extends RefCounted
## The plan geometry of a turn (`P3-3c`): the curve a car drives from one road's
## mouth to the next, and whether two such curves meet. Pure and static, so
## `TrafficSystem` and `verify_traffic.gd` ask the same arithmetic.

## Samples a turn curve's length is measured over.
const CURVE_SAMPLES: int = 8


## Whether two turn paths meet in plan: a stretch of each within `reach_m` of
## the other at more than the angle whose sine is `min_sin`, or within `touch_m`
## at any angle. Under the angle the two run side by side or head to head, and
## meet only where their bodies would (seeds 4 and 7: a car joining a road ran
## alongside one crossing its mouth, nearer than its width).
static func paths_cross(
	a: PackedVector3Array, b: PackedVector3Array, reach_m: float, touch_m: float, min_sin: float
) -> bool:
	var a_plan: PackedVector2Array = _plan_points(a)
	var b_plan: PackedVector2Array = _plan_points(b)
	var reach: float = maxf(reach_m, touch_m)
	if not _plan_bounds(a_plan).grow(reach).intersects(_plan_bounds(b_plan)):
		return false
	var b_dirs: PackedVector2Array = []
	b_dirs.resize(b_plan.size() - 1)
	for j: int in b_dirs.size():
		b_dirs[j] = (b_plan[j + 1] - b_plan[j]).normalized()
	for i: int in a_plan.size() - 1:
		var a0: Vector2 = a_plan[i]
		var a1: Vector2 = a_plan[i + 1]
		if a0.is_equal_approx(a1):
			continue
		var a_dir: Vector2 = (a1 - a0).normalized()
		for j: int in b_dirs.size():
			if b_dirs[j] == Vector2.ZERO:
				continue
			var crossing: bool = absf(a_dir.cross(b_dirs[j])) >= min_sin
			if segment_gap(a0, a1, b_plan[j], b_plan[j + 1]) < (reach_m if crossing else touch_m):
				return true
	return false


static func _plan_points(path: PackedVector3Array) -> PackedVector2Array:
	var plan: PackedVector2Array = []
	plan.resize(path.size())
	for index: int in path.size():
		plan[index] = Vector2(path[index].x, path[index].z)
	return plan


static func _plan_bounds(plan: PackedVector2Array) -> Rect2:
	var bounds := Rect2(plan[0], Vector2.ZERO)
	for point: Vector2 in plan:
		bounds = bounds.expand(point)
	return bounds


## The least plan distance between two segments: 0 where they cross.
static func segment_gap(a0: Vector2, a1: Vector2, b0: Vector2, b1: Vector2) -> float:
	if Geometry2D.segment_intersects_segment(a0, a1, b0, b1) != null:
		return 0.0
	return minf(
		minf(
			a0.distance_to(Geometry2D.get_closest_point_to_segment(a0, b0, b1)),
			a1.distance_to(Geometry2D.get_closest_point_to_segment(a1, b0, b1))
		),
		minf(
			b0.distance_to(Geometry2D.get_closest_point_to_segment(b0, a0, a1)),
			b1.distance_to(Geometry2D.get_closest_point_to_segment(b1, a0, a1))
		)
	)


## The curve's middle control point: where the line in along `into` meets the
## line out along `out`, in plan, or the chord's middle where they do not meet
## ahead of both (straight on, or a kink the wrong way).
static func turn_control(p0: Vector3, into: Vector3, p2: Vector3, out: Vector3) -> Vector3:
	var chord: Vector3 = p2 - p0
	var middle: Vector3 = p0.lerp(p2, 0.5)
	var denom: float = into.x * out.z - into.z * out.x
	if absf(denom) < 0.05:
		return middle
	var a: float = (chord.x * out.z - chord.z * out.x) / denom
	var b: float = (into.x * chord.z - chord.x * into.z) / denom
	var reach: float = Vector2(chord.x, chord.z).length()
	if a <= 0.0 or b <= 0.0 or a > reach * 2.0 or b > reach * 2.0:
		return middle
	var meet: Vector3 = p0 + into * a
	meet.y = middle.y
	return meet


static func curve_point(p0: Vector3, p1: Vector3, p2: Vector3, u: float) -> Vector3:
	var v: float = 1.0 - u
	return p0 * (v * v) + p1 * (2.0 * v * u) + p2 * (u * u)


static func curve_length(p0: Vector3, p1: Vector3, p2: Vector3) -> float:
	var total: float = 0.0
	var last: Vector3 = p0
	for index: int in range(1, CURVE_SAMPLES + 1):
		var point: Vector3 = curve_point(p0, p1, p2, float(index) / CURVE_SAMPLES)
		total += last.distance_to(point)
		last = point
	return total
