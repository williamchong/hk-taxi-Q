class_name StreetPlate
extends RefCounted
## The street plate's tuning, and the one substitution it applies (`P3-24`).
##
## **One file, one reader.** `tuning/street_plate.json` is JSON rather than a
## `.tres` precisely so `tools/font_coverage.py` can read the same table this
## does — and the first version of that argument then shipped two GDScript
## parsers of it, one here and one in `verify_hud.gd`. Two parsers of one file
## drift, which is the thing the JSON's own header warns about.
##
## ⚠️ **Not a `GeneratedDocument`.** That loader is for versioned ETL output and
## carries a `schema_version` check plus a "re-run the pipeline" hint. This is
## committed, hand-authored tuning: there is no pipeline to re-run and no
## producer to be out of step with.

const PATH: String = "res://tuning/street_plate.json"


## The tuning object, or `{}` having said why.
static func load_tuning() -> Dictionary:
	var text: String = FileAccess.get_file_as_string(PATH)
	if text.is_empty():
		push_warning("street plate: %s is missing or empty" % PATH)
		return {}
	var parsed: Variant = JSON.parse_string(text)
	if parsed is Dictionary:
		return parsed
	push_warning("street plate: %s did not parse as an object" % PATH)
	return {}


## Swap any character the plate's font cannot draw for the same character in a
## form it can.
##
## ⚠️ **A display fix, and the published document keeps what the Transport
## Department wrote** (`Q54`). `啓超道` stays `啓超道` in `roadgraph.json`; only
## the pixels change. `tools/font_coverage.py` fails on a character that is in
## neither the font nor this table, so this can never silently draw a box.
static func substitute(text: String, table: Dictionary) -> String:
	if table.is_empty():
		return text
	var out: String = text
	for from: Variant in table:
		out = out.replace(from as String, table[from] as String)
	return out


## Set `label` at `size`, or at the largest size under it that fits `room` px.
## For the minimap's strip, which is the map's width whatever the name.
static func shrink_to(label: Label, size: int, room: float) -> void:
	label.add_theme_font_size_override(&"font_size", fitted_size(label, size, room))


## The size `label`'s text is set at: `size`, or the largest under it that fits.
##
## ⚠️ Measured off the FONT, not off `Label.get_minimum_size()`: a label that is
## not in the tree, or whose text changed this frame, reports a stale or empty
## size, and a fit that reads 0 never shrinks anything.
static func fitted_size(label: Label, size: int, room: float) -> int:
	var font: Font = label.get_theme_font(&"font")
	var wanted: float = font.get_string_size(label.text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, size).x
	return size if wanted <= room else floori(size * room / wanted)
