## Where the ETL's hero-building placements live, and how to read them.
##
## The fourth locator, for the reason the other three exist: the runtime
## placer (`landmarks.gd`) and `verify_landmarks.gd` both want the document,
## and a moved path that only one of them learns about fails silently in the
## other.
##
## Dev-only. `city.json` is what a shipped build reads and `CityManifest`
## (`P1-7`) resolves the path from it; this constant is what the tools use,
## and `verify_landmarks.gd` asserts the two name the same file.
extends RefCounted

const GeneratedDocument = preload("res://scripts/city/generated_document.gd")

const PATH: String = "res://assets/generated/landmarks.json"

## Schema this understands, matching `LANDMARKS_SCHEMA` in
## `etl/pipeline/export.py`.
const SCHEMA_VERSION: int = 1


## The parsed landmark document, or an empty dictionary with a pushed message.
##
## Takes a path so the runtime placer can pass the one the manifest resolved
## (`P1-7`: the manifest is the shipping route) while the schema and the hint
## stay paired here — the locator remains the only loader of this document.
static func load_landmarks(path: String = PATH) -> Dictionary:
	return GeneratedDocument.load_object(path, SCHEMA_VERSION, missing_hint())


## A landmark's placement as a transform, or `null` where it has none.
##
## The one place the bearing convention is converted (`P3-6`): `rot_y_deg` is a
## compass bearing — 0 at north rising eastward, `CityManifest.bearing_deg`'s
## convention — and game north is -Z, so a bearing becomes a **negative**
## rotation about +Y. Null rather than `Transform3D.IDENTITY`, because the
## region origin is a real place a hero could stand and a malformed entry
## should not look like a successful placement there.
static func placement_of(entry: Dictionary) -> Variant:
	var transform: Dictionary = entry.get("transform", {}) as Dictionary
	var values: Array = transform.get("pos", []) if transform.get("pos") is Array else []
	if values.size() < 3:
		return null
	var basis := Basis(Vector3.UP, deg_to_rad(-float(transform.get("rot_y_deg", 0.0))))
	return Transform3D(basis, Vector3(values[0], values[1], values[2]))


## A landmark's excluded source footprint as an AABB, or `null` where the
## document carries none. Null for the reason `placement_of` gives: a zero-size
## box sits at the region origin, a real place, and a missing footprint must
## not look like an empty one there.
static func excluded_bounds_of(entry: Dictionary) -> Variant:
	var corners: Array = (
		entry.get("excluded_bounds") if entry.get("excluded_bounds") is Array else []
	)
	if corners.size() != 2:
		return null
	return CityManifest.box(CityManifest.point(corners[0]), CityManifest.point(corners[1]))


## Message for the case that reads as "there are no heroes" rather than an error.
static func missing_hint() -> String:
	return (
		"No landmark placements at %s. Run the ETL and copy its output there:\n" % PATH
		+ "  python -m pipeline.export --city hong_kong --region wan_chai\n"
		+ "  tools/sync_generated.sh hong_kong wan_chai"
	)
