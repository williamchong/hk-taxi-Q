class_name Minimap
extends Control
## The street map, bottom-left above the plate (`P3-44`, `Q136`, `Q138`).
##
## **One component with the street name** (the user's call, `Q136`): the map on
## top, the name of the street under the car in a strip along the bottom, one
## keyline round both — a GPS's current-road bar. `Q80` had already called the
## two "one question". `hud.gd` owns the strip's lettering; this owns its box.
##
## **Driving only.** Roads, which way they run, and the car. No route is drawn and none will be
## without `Q137` reopening; the destination pip arrives with `P3-1a`, which is
## the first thing that has a destination.
##
## **The city's voice**, by `hud_style.gd`'s rule: a light field like the plate
## under it, because a map of the streets is the city speaking. The chevron is
## the one thing on it that is the car.
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
## The map's share of this control: everything above the strip.
var _map_px: Vector2 = Vector2.ZERO

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
	_map_px = map_px
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
	_field.add_child(_marker)

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


## Put `car` on the anchor, nose along `forward`.
func follow(car: Vector3, forward: Vector3) -> void:
	var anchor_px: Vector2 = _map_px * _mapping.anchor
	_roads.transform = MinimapProjection.roads_transform(
		car, forward, _mapping.heading_up, _px_per_m, anchor_px
	)
	_marker.position = anchor_px
	_marker.rotation = MinimapProjection.marker_rotation(forward, _mapping.heading_up)


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
