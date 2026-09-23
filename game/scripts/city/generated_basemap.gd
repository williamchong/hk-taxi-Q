## Where the ETL's minimap ground lives — the harbour and the parks — and how to
## read it (2026-09-24).
##
## A locator on `generated_fence.gd`'s terms: the minimap and `verify_city.gd`
## both want the document, and a moved path only one of them learns about fails
## silently in the other. `city.json` is what a shipped build resolves the path
## from (`CityManifest.basemap_path`); this constant is what the tools use.
extends RefCounted

const GeneratedDocument = preload("res://scripts/city/generated_document.gd")
const GeneratedRegions = preload("res://scripts/city/generated_regions.gd")

const FILE: String = "basemap.json"

## Schema this understands, matching `BASEMAP_SCHEMA` in `etl/pipeline/basemap.py`.
const SCHEMA_VERSION: int = 1


## Where a region's copy is; `GeneratedRegions.selected()` for "".
static func path(region: String = "") -> String:
	return GeneratedRegions.dir(region) + FILE


## The parsed document, or an empty dictionary with a pushed message.
static func load_basemap(at: String = "") -> Dictionary:
	return GeneratedDocument.load_object(
		at if not at.is_empty() else path(), SCHEMA_VERSION, missing_hint()
	)


static func missing_hint() -> String:
	return (
		"No minimap ground at %s. Run the ETL and copy its output there:\n" % path()
		+ "  python -m pipeline.basemap --region wan_chai\n"
		+ "  tools/sync_generated.sh wan_chai causeway_bay"
	)
