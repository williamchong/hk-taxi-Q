class_name EngineNotices
extends RefCounted
## The engine's third-party notices, composed at runtime from the engine's own
## tables (`P6-1`, `LICENSING.md` item 5): every component the binary bundles,
## its copyright holders and the licence each part is under, then every
## licence's full text once, then the bundled add-ons' (`ADDONS`).
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
## Add-ons the game bundles beside the engine, each with the licence file it
## ships in (`Q256`): name to path. Read at runtime like the engine's tables,
## so the words are the vendored release's. The file has no resource type, so
## every export preset names it in `include_filter`, or it never reaches a PCK.
const ADDONS: Dictionary[String, String] = {
	"PostHog Godot SDK": "res://addons/posthog/LICENSE",
}


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
	lines.append("")
	lines.append(RULE)
	lines.append("BUNDLED ADD-ONS")
	lines.append(RULE)
	for addon: String in ADDONS:
		lines.append("")
		lines.append(addon)
		lines.append("")
		var text: String = FileAccess.get_file_as_string(ADDONS[addon])
		if text.is_empty():
			push_warning("engine notices: %s did not load" % ADDONS[addon])
		lines.append(text.strip_edges())
	return "\n".join(lines)
