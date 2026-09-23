class_name Minimap
extends Control
## The street map, bottom-left above the plate (`P3-44`, `Q136`, `Q138`).
##
## **One component with the street name** (the user's call, `Q136`): the map on
## top, the name of the street under the car in a strip along the bottom, one
## keyline round both — a GPS's current-road bar. `Q80` had already called the
## two "one question". `hud.gd` owns the strip's lettering; this owns its box.
##
## **Driving only.** Roads, which way they run, the car, and since `P3-5a` the
## fare's pips: every pickup in the pool, and the one destination. No route is
## drawn and none will be without `Q137` reopening.
##
## The meter's housing, like every panel (`Q139`): light roads on black, and
## the chevron in the LED's red — the one thing on the map that is the car.
##
## Built once, moved by a transform: the roads are one static mesh in plan
## metres (`minimap_mesh.gd`) and `follow` only re-places it, so a turning map
## costs a matrix a frame and no geometry.

## How far a vertex may be dropped from its road, in design pixels: under what
## the slot can show. A property of the raster, not a look to tune.
const SUBPIXEL_PX: float = 0.4

var _mapping: MinimapProfile = null
## The ONE scale: the mesh's pixel floors are baked at it and `follow` places
## the mesh at it, so the two cannot drift apart.
var _px_per_m: float = 0.0
var _field: ChamferPanel = null
var _roads: MeshInstance2D = null
var _marker: Polygon2D = null
## The fare's marks (`P3-5a`): the pool's pips as one mesh under the roads,
## moved by `follow` for nothing; and the target's pin, the field's child so
## it stands upright whatever the map's heading, re-placed by `follow` at the
## roads' transform of its plan point.
var _pickups: MeshInstance2D = null
var _pin: Polygon2D = null
var _pin_plan: Vector2 = Vector2.ZERO
var _style: HudStyle = null

## Where the street name goes. Hidden until `hud.gd` has a street to put in it,
## and the map shows through until then.
var strip: ColorRect = null


## `map_px` is the layout's `minimap` size and `strip_px` its `street_plate`
## height, handed in because the stroke floor and the casing are pixels baked
## into a mesh of metres, and `size` is not known until the node is placed.
func setup(
	mapping: MinimapProfile, style: HudStyle, graph: RoadGraph, map_px: Vector2, strip_px: float
) -> void:
	_mapping = mapping
	_style = style
	mouse_filter = Control.MOUSE_FILTER_IGNORE

	# The field clips the roads to its own cut corners. ⚠️ `clip_children` masks
	# by the parent's drawn alpha, which is the second reason `map_field` must
	# be opaque — see `minimap_mesh.gd` for the first.
	_field = _panel("Field", style, style.map_field, Color.TRANSPARENT)
	_field.clip_children = CanvasItem.CLIP_CHILDREN_AND_DRAW

	_roads = MeshInstance2D.new()
	_roads.name = "Roads"
	_px_per_m = map_px.x / maxf(mapping.span_m, 0.001)
	var arrows: MinimapMesh.Arrows = null
	if mapping.arrow_px > 0.0:
		arrows = MinimapMesh.Arrows.new()
		arrows.length_m = mapping.arrow_px / _px_per_m
		arrows.spacing_m = mapping.arrow_spacing_px / _px_per_m
	_roads.mesh = MinimapMesh.build(
		MinimapMesh.strokes_of(graph, mapping.min_stroke_px / _px_per_m, SUBPIXEL_PX / _px_per_m),
		style.map_road,
		style.map_field,
		mapping.casing_px / _px_per_m,
		arrows
	)
	_field.add_child(_roads)

	# Rim and fill in ONE polygon node, by vertex colour: a `Line2D` rim was a
	# draw call of its own on a HUD that costs five in all.
	_marker = Polygon2D.new()
	_marker.name = "Car"
	var outer: PackedVector2Array = chevron(mapping.marker_px)
	# Shorter by four keylines: a chevron scales about its centre and its flanks
	# lie 0.37 of its length out, so that leaves them about one keyline of rim.
	var inner: PackedVector2Array = chevron(mapping.marker_px - style.edge_px * 4.0)
	_marker.polygon = outer + inner
	_marker.polygons = [
		PackedInt32Array(range(0, outer.size())),
		PackedInt32Array(range(outer.size(), outer.size() + inner.size()))
	]
	var inks := PackedColorArray()
	for index: int in outer.size() + inner.size():
		inks.append(style.map_marker_edge if index < outer.size() else style.map_marker)
	_marker.vertex_colors = inks
	# Placed once: the anchor never moves, and heading-up neither does the
	# chevron — the map turns under it.
	_marker.position = map_px * mapping.anchor
	_field.add_child(_marker)

	# The target's pin (the user's call: an icon, not a dot), its tip on the
	# point. Under the car, over the roads; hidden until there is a target.
	_pin = Polygon2D.new()
	_pin.name = "Pin"
	_pin.polygon = pin(style.map_pin_px)
	_pin.color = style.map_destination
	_pin.visible = false
	_field.add_child(_pin)
	_field.move_child(_pin, _marker.get_index())

	# A child of the field so the chamfer clips its two bottom corners too, and
	# after the roads so it covers them. The rule above it is the keyline's.
	strip = ColorRect.new()
	strip.name = "Strip"
	strip.color = style.plate_field
	strip.mouse_filter = Control.MOUSE_FILTER_IGNORE
	strip.visible = false
	strip.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	strip.offset_top = -strip_px
	_field.add_child(strip)
	var rule := ColorRect.new()
	rule.name = "Rule"
	rule.color = style.plate_edge
	rule.mouse_filter = Control.MOUSE_FILTER_IGNORE
	rule.set_anchors_preset(Control.PRESET_TOP_WIDE)
	rule.offset_bottom = style.edge_px
	strip.add_child(rule)

	# The keyline is a sibling OVER the field, not the field's own edge: a
	# clipping parent draws before its children, so its edge would sit under the
	# roads that reach it.
	_panel("Frame", style, Color.TRANSPARENT, style.plate_edge)


## Every pickup in the pool as one mesh of pips, in plan metres under the
## roads' transform (`P3-5a`). Built once: the pool does not move.
func set_pickups(points: PackedVector3Array) -> void:
	if _pickups != null:
		_pickups.queue_free()
		_pickups = null
	if points.is_empty():
		return
	var vertices := PackedVector2Array()
	var colours := PackedColorArray()
	var shape: PackedVector2Array = pip(_style.map_pip_px / _px_per_m)
	for point: Vector3 in points:
		var at: Vector2 = MinimapProjection.plan(point)
		# A diamond is two triangles about its centre.
		for triangle: PackedVector2Array in [
			PackedVector2Array([shape[0], shape[1], shape[2]]),
			PackedVector2Array([shape[0], shape[2], shape[3]])
		]:
			for corner: Vector2 in triangle:
				vertices.append(at + corner)
				colours.append(_style.map_pickup)
	_pickups = MeshInstance2D.new()
	_pickups.name = "Pickups"
	_pickups.mesh = CanvasMesh.of(vertices, colours)
	_roads.add_child(_pickups)
	# Under the destination: the one pip that is a fare covers the pool's.
	_roads.move_child(_pickups, 0)


## Put the pin on the destination at `point`, or hide it.
func set_target(point: Vector3, shown: bool) -> void:
	if _pin.visible != shown:
		_pin.visible = shown
	if not shown:
		return
	_pin_plan = MinimapProjection.plan(point)
	_pin.position = _roads.transform * _pin_plan


## Put `car` on the anchor, nose along `forward`.
func follow(car: Vector3, forward: Vector3) -> void:
	var anchor_px: Vector2 = _marker.position
	_roads.transform = MinimapProjection.roads_transform(
		car, forward, _mapping.heading_up, _px_per_m, anchor_px
	)
	if not _mapping.heading_up:
		_marker.rotation = MinimapProjection.marker_rotation(forward, false)
	if _pin.visible:
		_pin.position = _roads.transform * _pin_plan


func _panel(node_name: String, style: HudStyle, fill: Color, edge: Color) -> ChamferPanel:
	var panel := ChamferPanel.new()
	panel.name = node_name
	panel.chamfer_px = style.chamfer_px
	panel.fill = fill
	panel.edge = edge
	panel.edge_px = style.edge_px
	panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(panel)
	return panel


## A pin: a map marker `tall` px high with its TIP at the origin — a head the
## width of half its height over a point — so it stands on its place.
static func pin(tall: float) -> PackedVector2Array:
	var head: float = tall * 0.55
	var half: float = head * 0.5
	var centre: float = -tall + half
	var points := PackedVector2Array()
	# The head as a half-round of eight segments, then the two flanks to the tip.
	for index: int in 9:
		var angle: float = PI + PI * index / 8.0
		points.append(Vector2(cos(angle) * half, centre + sin(angle) * half))
	points.append(Vector2.ZERO)
	return points


## A pip: a diamond `across` wide about its own centre, which turns with the
## map and still reads as a point.
static func pip(across: float) -> PackedVector2Array:
	var half: float = across * 0.5
	return PackedVector2Array(
		[Vector2(0.0, -half), Vector2(half, 0.0), Vector2(0.0, half), Vector2(-half, 0.0)]
	)


## The car, pointing up (`-Y`): a notched arrowhead `length` tall about its own
## centre, so rotating it turns it on the spot.
static func chevron(length: float) -> PackedVector2Array:
	var half: float = length * 0.5
	return PackedVector2Array(
		[
			Vector2(0.0, -half),
			Vector2(half * 0.8, half),
			Vector2(0.0, half * 0.45),
			Vector2(-half * 0.8, half),
		]
	)
