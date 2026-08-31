## Where the ETL's barrier placements live, and how to read them (`P3-29`).
##
## A locator for the reason the others exist: the runtime placer (`fence.gd`)
## and `verify_fence.gd` both want the document, and a moved path that only one
## of them learns about fails silently in the other.
##
## Dev-only. `city.json` is what a shipped build reads and `CityManifest`
## (`P1-7`) resolves the path from it; this constant is what the tools use, and
## `verify_fence.gd` asserts the two name the same file.
extends RefCounted

const GeneratedDocument = preload("res://scripts/city/generated_document.gd")

const PATH: String = "res://assets/generated/fence.json"

## Schema this understands, matching `FENCE_SCHEMA` in `etl/pipeline/fence.py`.
const SCHEMA_VERSION: int = 1


## The parsed fence document, or an empty dictionary with a pushed message.
static func load_fence(path: String = PATH) -> Dictionary:
	return GeneratedDocument.load_object(path, SCHEMA_VERSION, missing_hint())


## One barrier's placement as a transform, or `null` where it has none.
##
## 🔴 **The facing arrives as a direction, not as a compass bearing, and that is
## deliberate.** `GeneratedLandmarks.placement_of` converts `rot_y_deg` and is
## the one place in the repo that owns that convention; a second producer of it
## would be a sign error waiting to happen on a layer where the wrong facing
## renders as a perfectly good barrier turned the wrong way (`Q62`). A vector
## goes through `RoadSpawn.basis_facing`, which has no convention to get wrong
## and is the same route the car takes.
##
## Null rather than `Transform3D.IDENTITY`, on `placement_of`'s reasoning: the
## region origin is a real place a barrier could stand, so a malformed entry
## must not look like a successful placement there.
static func placement_of(entry: Dictionary) -> Variant:
	# ⚠️ Shapes checked here rather than through `CityManifest.point`, which
	# pushes its own error and returns `Vector3.ZERO`: a malformed entry would
	# then be reported twice and still placed at the region origin, which is the
	# one outcome the null return exists to prevent.
	var where: Array = entry.get("position") if entry.get("position") is Array else []
	var aim: Array = entry.get("facing") if entry.get("facing") is Array else []
	if where.size() != 3 or aim.size() != 3:
		return null
	# A zero or purely vertical facing would make `looking_at` fall back on an
	# arbitrary basis, which is the silent half of this failure. Guarded here
	# rather than inside `basis_facing`, which returns `IDENTITY` for it — a
	# barrier at a plausible-looking angle is exactly what must not be placed.
	var facing := Vector3(aim[0], 0.0, aim[2])
	if facing.length_squared() <= 0.0:
		return null
	# 🔴 `RoadSpawn.basis_facing` rather than a second `looking_at` call: it is
	# the one place that flattens and normalises a direction into a level basis,
	# and it carries the note that `looking_at` puts **-Z** on the target, which
	# is what the barrier's own front face has to agree with.
	return Transform3D(RoadSpawn.basis_facing(facing), Vector3(where[0], where[1], where[2]))


## Message for the case that reads as "nothing is fenced" rather than an error.
static func missing_hint() -> String:
	return (
		"No barrier placements at %s. Run the ETL and copy its output there:\n" % PATH
		+ "  python -m pipeline.fence --region wan_chai\n"
		+ "  tools/sync_generated.sh hong_kong wan_chai"
	)
