class_name SheetImage
extends RefCounted
## The 成績表 saved as a picture (`P3-80`, `Q188`; the user's call 2026-11-06:
## "just export the result sheet as image").
##
## **The sheet the player is reading, copied, never the screen cropped.** The
## page's own column is duplicated into a `SubViewport` its own size on the
## housing's field, so every device gives the same picture whatever its window,
## and the blurred city behind the panel — our render of the government's data
## — stays in the game. A copy, not a second `LedgerCard.build`: the picture is
## what was on screen, row for row, with no second path that could drift.
##
## 🔴 **Not offered on a phone** (the user's call): the app and the phone's
## browser alike, since a screenshot is one button press there. Godot 4.7 has no
## share sheet and no save-to-Photos call (its class reference, checked
## 2026-11-06), so a phone needs a plugin; `is_phone` is the one line a plugin
## lifts. On a computer the file goes to Pictures and its folder opens; on the
## web it is a download.

const FILE_STEM: String = "hk-taxi-q-sheet"
## A sheet's row of buttons (`StartMenu._foot_row`), which the copy leaves out:
## the buttons are not the sheet.
const FOOT: String = "Foot"


## Whether this device gets the button.
static func offered() -> bool:
	return not is_phone(OS.has_feature)


## `has_feature` answers `OS.has_feature`'s question; handed in so a check can
## ask about a phone from a desk.
static func is_phone(has_feature: Callable) -> bool:
	return (
		has_feature.call("mobile") or has_feature.call("web_android") or has_feature.call("web_ios")
	)


## The viewport the picture is drawn in, holding a copy of `column` on the
## housing's field: laid out at the column's own size on screen, its buttons
## left off, padded like the panel, and drawn `sheet_image_scale` times over.
## Not in the tree; `shoot` adds it.
static func stage(column: Control, profile: MenuProfile, style: HudStyle) -> SubViewport:
	# The column's size, not `ledger_px`: RECORD's runs and best stand over
	# the tables, and a fixed box cut the total off its foot.
	var content: Vector2 = column.size
	var source_foot: Control = column.get_node_or_null(FOOT)
	if source_foot != null:
		content.y -= source_foot.size.y + column.get_theme_constant(&"separation")
	# A phone's sheet scrolls (`Q206`): the picture is the whole card, never the
	# window onto it.
	var source_scroll: Control = column.get_node_or_null(StartMenu.SCROLL)
	if source_scroll != null and source_scroll.get_child_count() > 0:
		content.y += (source_scroll.get_child(0) as Control).size.y - source_scroll.size.y
	var layout := Vector2i((content + Vector2.ONE * 2.0 * profile.credits_pad_px).ceil())
	var viewport := SubViewport.new()
	viewport.name = "SheetImage"
	viewport.transparent_bg = false
	viewport.size_2d_override = layout
	viewport.size_2d_override_stretch = true
	viewport.size = Vector2i((Vector2(layout) * profile.sheet_image_scale).round())
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	var field := ColorRect.new()
	field.name = "Field"
	field.color = style.plate_field
	field.set_anchors_preset(Control.PRESET_FULL_RECT)
	viewport.add_child(field)
	var pad: MarginContainer = StartMenu.padded(profile.credits_pad_px)
	pad.set_anchors_preset(Control.PRESET_FULL_RECT)
	viewport.add_child(pad)
	var copy: Control = column.duplicate()
	copy.name = "Column"
	copy.visible = true
	var foot: Node = copy.get_node_or_null(FOOT)
	if foot != null:
		copy.remove_child(foot)
		foot.free()
	var scroll: ScrollContainer = copy.get_node_or_null(StartMenu.SCROLL)
	if scroll != null:
		# With scrolling off the scroll's minimum height is the card's, so the
		# copy lays out the whole card from its top, and with no bar to clear
		# the card runs to the picture's right edge.
		scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
		scroll.scroll_vertical = 0
		scroll.get_node(StartMenu.GUTTER).add_theme_constant_override(&"margin_right", 0)
	pad.add_child(copy)
	return viewport


## Draw `stage`'s viewport under `host` and read it back.
static func shoot(host: Node, column: Control, profile: MenuProfile, style: HudStyle) -> Image:
	var viewport: SubViewport = stage(column, profile, style)
	host.add_child(viewport)
	# One frame lays the containers out, the next draws them.
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	# Gone with `host` if the menu left while it drew: no picture, and `save` says so.
	if not is_instance_valid(viewport):
		return null
	var image: Image = viewport.get_texture().get_image()
	viewport.queue_free()
	return image


## Save `image` where this device keeps pictures: what was written, or "" having
## said why. The web's is a download, named.
static func save(image: Image) -> String:
	if image == null or image.is_empty():
		push_warning("sheet image: nothing was drawn")
		return ""
	var stamp: String = Time.get_datetime_string_from_system().replace(":", "").replace("T", "-")
	var file_name: String = "%s-%s.png" % [FILE_STEM, stamp]
	if OS.has_feature("web"):
		JavaScriptBridge.download_buffer(image.save_png_to_buffer(), file_name, "image/png")
		return file_name
	var folder: String = OS.get_system_dir(OS.SYSTEM_DIR_PICTURES)
	if folder.is_empty() or not DirAccess.dir_exists_absolute(folder):
		folder = ProjectSettings.globalize_path("user://")
	var path: String = folder.path_join(file_name)
	var error: Error = image.save_png(path)
	if error != OK:
		push_warning("sheet image: %s not written (%s)" % [path, error_string(error)])
		return ""
	OS.shell_show_in_file_manager(path)
	return path
