class_name EngineNotices
extends RefCounted
## The engine's third-party notices, composed at runtime from the engine's own
## tables (`P6-1`, `LICENSING.md` item 5): every component the binary bundles,
## its copyright holders and the licence each part is under, then every
## licence's full text once.
##
## Read from the engine, never copied into the repo: the notices belong to the
## build that ships, and a text pasted at one version is wrong the release
## after a point upgrade. `Engine.get_copyright_info()` and
## `Engine.get_license_info()` are the two tables the editor's own
## "Third-party Licenses" tab is drawn from, compiled into every export
## template, so the store build and the web build carry the same words.
##
## ⚠️ `Engine.get_license_text()` is NOT this: it is Godot's own MIT notice
## alone, one screen of text, and shipping only that leaves 100 components
## unacknowledged. `verify_menu.gd` holds that the composed text names every
## component and carries every licence's text.

const RULE: String = "----------------------------------------------------------------"


## The whole text, English, as the engine states it.
static func compose() -> String:
	var version: Dictionary = Engine.get_version_info()
	var lines: PackedStringArray = []
	lines.append("Godot Engine %s" % str(version.get("string", "")))
	lines.append("")
	lines.append(Engine.get_license_text().strip_edges())
	lines.append("")
	lines.append(RULE)
	lines.append("THIRD-PARTY COMPONENTS")
	lines.append(RULE)
	for component: Dictionary in Engine.get_copyright_info():
		lines.append("")
		lines.append(str(component.get("name", "")))
		for part: Dictionary in component.get("parts", []):
			var files: PackedStringArray = part.get("files", PackedStringArray())
			if not files.is_empty():
				lines.append("  Files: %s" % ", ".join(files))
			for holder: String in part.get("copyright", PackedStringArray()):
				lines.append("  Copyright (c) %s" % holder)
			lines.append("  License: %s" % str(part.get("license", "")))
	lines.append("")
	lines.append(RULE)
	lines.append("LICENSES")
	lines.append(RULE)
	var licences: Dictionary = Engine.get_license_info()
	for id: String in licences:
		lines.append("")
		lines.append(id)
		lines.append("")
		lines.append(str(licences[id]).strip_edges())
	return "\n".join(lines)
