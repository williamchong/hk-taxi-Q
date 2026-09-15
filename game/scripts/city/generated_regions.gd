## Which regions are synced, and where each one's bundle lives (`P5-9b`).
##
## `tools/sync_generated.sh <region>...` writes one directory per region under
## `ROOT` and names them, in argument order, in `regions.json`. The first is the
## **frame**: every other resident region is placed at its `city_offset` minus
## the frame's (`P5-9c`). This file is the one place the generated root is
## spelled — every locator and `CityManifest` ask `dir()` for their directory —
## so a second region never needs a second constant.
##
## ⚠️ **The list is build output, not tuning.** It records which bundles were
## synced; hard rule 4 is about values someone chooses, and does not reach it.
##
## ⚠️ **No list is not an error here.** A fresh clone has none, and neither does a
## tree synced before `P5-9b`; `dir()` then answers the bare root, the document a
## caller asked for is not there, and that caller's own missing hint says what to
## run — the way a fresh clone has always degraded. `verify_city.gd` is what fails.
extends RefCounted

const GeneratedDocument = preload("res://scripts/city/generated_document.gd")

const ROOT: String = "res://assets/generated/"

const PATH: String = ROOT + "regions.json"

## Schema this understands, matching what `tools/sync_generated.sh` writes.
const SCHEMA_VERSION: int = 1

## `--region=<id>` picks which listed region a single-region reader opens — how
## `check.sh` runs each verify tool once per region. Absent, it is the frame.
const REGION_ARG: String = "--region="


## The synced regions in `regions.json` order, the frame first; empty where no
## list was written.
static func listed() -> PackedStringArray:
	if not FileAccess.file_exists(PATH):
		return PackedStringArray()
	var document: Dictionary = GeneratedDocument.load_object(PATH, SCHEMA_VERSION, "")
	var found := PackedStringArray()
	for region: Variant in document.get("regions", []) as Array:
		found.append(str(region))
	return found


## The region every other one is placed relative to, or "" with no list.
static func frame() -> String:
	var regions: PackedStringArray = listed()
	return "" if regions.is_empty() else regions[0]


## The region a reader that holds one region opens: `--region=`, else the frame.
static func selected() -> String:
	var asked: String = Cmdline.value(REGION_ARG)
	return asked if not asked.is_empty() else frame()


## A region's bundle directory, with a trailing slash; `selected()` for "".
static func dir(region: String = "") -> String:
	var id: String = region if not region.is_empty() else selected()
	return ROOT if id.is_empty() else ROOT + id + "/"
