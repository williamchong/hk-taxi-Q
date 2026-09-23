class_name Minimap
extends Control
## The street map, bottom-left above the plate (`P3-44`, `Q136`, `Q138`).
##
## **One component with the street name** (the user's call, `Q136`): the map on
## top, the name of the street under the car in a strip along the bottom, one
## keyline round both — a GPS's current-road bar. `Q80` had already called the
## two "one question". `hud.gd` owns the strip's lettering; this owns its box.
##
## **Driving only.** The harbour and the parks under the roads (`basemap.json`),
## roads with the main ones apart, the car, and since `P3-5a` the fare's pins: every
## pending customer while no one is aboard, the one destination once hailed,
## and an arrow on the border toward whichever is the target while it is off
## the map. The one-way arrows are off (`minimap.md`). No route is
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
const GeneratedBasemap = preload("res://scripts/city/generated_basemap.gd")
const GeneratedRegions = preload("res://scripts/city/generated_regions.gd")

const SUBPIXEL_PX: float = 0.4

var _mapping: MinimapProfile = null
## The ONE scale: the mesh's pixel floors are baked at it and `follow` places
## the mesh at it, so the two cannot drift apart.
var _px_per_m: float = 0.0
var _field: ChamferPanel = null
var _roads: MeshInstance2D = null
var _marker: Polygon2D = null
## The fare's marks (`P3-5a`): the destination's pin and one pin per pending
## customer, the field's children so they stand upright whatever the map's
## heading, each re-placed by `follow` at the roads' transform of its plan
## point.
var _pin: Polygon2D = null
var _pin_plan: Vector2 = Vector2.ZERO
var _pending: Array[Polygon2D] = []
var _pending_plan: PackedVector2Array = PackedVector2Array()
var _pending_shown: bool = true
## Indices into `_pending` the fare loop is withholding (`withhold`).
var _withheld: PackedInt32Array = PackedInt32Array()
## The target's arrow on the map's border while the target is off it (the
## user's call): where the pin would be if the map were bigger.
var _beacon: Polygon2D = null
var _beacon_plan: Vector2 = Vector2.ZERO
var _beacon_on: bool = false
## Where the beacon may stand: the map's slot — `map_px`, which the strip sits
## below, not in — in from its keyline by the beacon's own size so it clears
## the chamfered corners.
var _beacon_room: Rect2 = Rect2()
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
		style.map_road_main,
		style.map_field,
		mapping.casing_px / _px_per_m,
		arrows,
		_ground(graph, style)
	)
	_field.add_child(_roads)

	_marker = _rimmed("Car", chevron, mapping.marker_px, style.map_marker)
	# Placed once: the anchor never moves, and heading-up neither does the
	# chevron — the map turns under it.
	_marker.position = map_px * mapping.anchor

	# The target's pin (the user's call: an icon, not a dot), its tip on the
	# point. Under the car, over the roads; hidden until there is a target.
	_pin = Polygon2D.new()
	_pin.name = "Pin"
	_pin.polygon = pin_shape(style.map_pin_px)
	_pin.color = style.map_destination
	_pin.visible = false
	_field.add_child(_pin)
	_field.move_child(_pin, _marker.get_index())

	# Over the pins, under the car; hidden until a target leaves the map.
	# A plain triangle, not the car's notched chevron: nothing on the map but
	# the car may read as the car.
	_beacon = _rimmed("Beacon", pointer, style.map_beacon_px, style.map_destination)
	_beacon.visible = false
	_field.move_child(_beacon, _marker.get_index())
	var inset: float = style.map_beacon_px
	_beacon_room = Rect2(Vector2(inset, inset), map_px - Vector2(inset * 2.0, inset * 2.0))

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


## Every resident region's water and parks, each moved to its place in the
## frame the graph is in. A region whose document is missing adds nothing: the
## map still has its roads, and `verify_city` reports the file.
static func _ground(graph: RoadGraph, style: HudStyle) -> MinimapMesh.Ground:
	var ground := MinimapMesh.Ground.new()
	for region: String in GeneratedRegions.resident():
		var manifest: CityManifest = CityManifest.load_manifest(region)
		if manifest == null or manifest.basemap_path.is_empty():
			continue
		var offset: Vector3 = graph.region_offset(region)
		ground.add(
			GeneratedBasemap.load_basemap(manifest.basemap_path),
			Vector2(offset.x, offset.z),
			style.map_water,
			style.map_park
		)
	return ground


## Every pending customer as an upright pin (the user's call: all of them,
## like a map, not the closest alone). The field's children, re-placed by
## `follow`; shown only while no one is aboard (`show_pending`).
func set_pickups(points: PackedVector3Array) -> void:
	for pin: Polygon2D in _pending:
		pin.queue_free()
	_pending.clear()
	_pending_plan.clear()
	var shape: PackedVector2Array = pin_shape(_style.map_pending_px)
	for point: Vector3 in points:
		var pin := Polygon2D.new()
		pin.name = "Pending%d" % _pending.size()
		pin.polygon = shape
		pin.color = _style.map_pickup
		pin.visible = _pending_shown and not _withheld.has(_pending.size())
		_field.add_child(pin)
		# Under the destination's pin and the car, over the roads.
		_field.move_child(pin, _pin.get_index())
		_pending.append(pin)
		_pending_plan.append(MinimapProjection.plan(point))
	_place_pending()


## Show or hide every pending customer's pin at once.
func show_pending(shown: bool) -> void:
	if _pending_shown == shown:
		return
	_pending_shown = shown
	_show_pins()
	_place_pending()


## Hide the pending pins at `indices`, the pickups the fare loop would refuse
## right now (`FareSystem.withheld_pickups`), and show the rest.
func withhold(indices: PackedInt32Array) -> void:
	if _withheld == indices:
		return
	_withheld = indices
	_show_pins()


func _show_pins() -> void:
	for index: int in _pending.size():
		var shown: bool = _pending_shown and not _withheld.has(index)
		if _pending[index].visible != shown:
			_pending[index].visible = shown


func _place_pending() -> void:
	if not _pending_shown:
		return
	for index: int in _pending.size():
		_pending[index].position = _roads.transform * _pending_plan[index]


## Put the destination's pin on `point`, or hide it.
func set_target(point: Vector3, shown: bool) -> void:
	if _pin.visible != shown:
		_pin.visible = shown
	if not shown:
		return
	_pin_plan = MinimapProjection.plan(point)
	_pin.position = _roads.transform * _pin_plan


## Point the border's arrow at `point` while it is off the map, in `ink` — the
## destination's red or a pending customer's amber — or put it away.
func set_beacon(point: Vector3, shown: bool, ink: Color) -> void:
	_beacon_on = shown
	_beacon_plan = MinimapProjection.plan(point)
	if shown:
		_fill(_beacon, ink)
	_place_beacon()


func _place_beacon() -> void:
	var at: Vector2 = Vector2.INF
	if _beacon_on:
		at = beacon_point(_beacon_room, _marker.position, _roads.transform * _beacon_plan)
	var shown: bool = at.is_finite()
	if _beacon.visible != shown:
		_beacon.visible = shown
	if not shown:
		return
	_beacon.position = at
	# The chevron points up (`-Y`), so a quarter turn past the heading's angle.
	_beacon.rotation = (at - _marker.position).angle() + PI * 0.5


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
	_place_pending()
	_place_beacon()


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


## `outline(length)` — `chevron` or `pointer` — in `fill`, rimmed in the
## marker's edge colour.
## Rim and fill in ONE polygon node, by vertex colour — outer ring first, fill
## second: a `Line2D` rim was a draw call of its own on a HUD that costs five in
## all.
func _rimmed(node_name: String, outline: Callable, length: float, fill: Color) -> Polygon2D:
	var shape := Polygon2D.new()
	shape.name = node_name
	var outer: PackedVector2Array = outline.call(length)
	# Shorter by four keylines, about the outline's own centre: the chevron's
	# flanks lie 0.37 of its length out, so that leaves them about one keyline
	# of rim, and `pointer` is centred on its centroid for the same even rim.
	var inner: PackedVector2Array = outline.call(length - _style.edge_px * 4.0)
	shape.polygon = outer + inner
	shape.polygons = [
		PackedInt32Array(range(0, outer.size())),
		PackedInt32Array(range(outer.size(), outer.size() + inner.size()))
	]
	var inks := PackedColorArray()
	for index: int in outer.size() + inner.size():
		inks.append(_style.map_marker_edge if index < outer.size() else fill)
	shape.vertex_colors = inks
	_field.add_child(shape)
	return shape


## Recolour `shape`'s fill — `_rimmed`'s second polygon — to `ink`, writing
## nothing when it already is.
static func _fill(shape: Polygon2D, ink: Color) -> void:
	var inks: PackedColorArray = shape.vertex_colors
	var fill: PackedInt32Array = shape.polygons[1]
	if inks[fill[0]] == ink:
		return
	for index: int in fill:
		inks[index] = ink
	shape.vertex_colors = inks


## Where the border's arrow stands for a target at `at`, in slot pixels: on the
## edge of `room`, on the line from `from` (the car, inside it) toward the
## target — or `Vector2.INF` while the target is inside `room`, where its own
## pin shows it.
static func beacon_point(room: Rect2, from: Vector2, at: Vector2) -> Vector2:
	if room.has_point(at):
		return Vector2.INF
	var toward: Vector2 = at - from
	var reach: float = 1.0
	if toward.x > 0.0:
		reach = minf(reach, (room.end.x - from.x) / toward.x)
	elif toward.x < 0.0:
		reach = minf(reach, (room.position.x - from.x) / toward.x)
	if toward.y > 0.0:
		reach = minf(reach, (room.end.y - from.y) / toward.y)
	elif toward.y < 0.0:
		reach = minf(reach, (room.position.y - from.y) / toward.y)
	# Never behind the car: with `from` outside `room` a negative reach would
	# stand the beacon on the far side, pointing away.
	return from + toward * maxf(reach, 0.0)


## A pin: a map marker `tall` px high with its TIP at the origin — a head the
## width of half its height over a point — so it stands on its place.
static func pin_shape(tall: float) -> PackedVector2Array:
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


## The beacon, pointing up (`-Y`): a plain arrowhead `length` tall, as wide as
## the car's, about its CENTROID — two thirds of the way to the tip — so the
## smaller copy `_rimmed` lays inside it leaves a rim all round, not a base.
static func pointer(length: float) -> PackedVector2Array:
	var half: float = length * 0.5
	var tip: float = length * 2.0 / 3.0
	var base: float = length / 3.0
	return PackedVector2Array(
		[Vector2(0.0, -tip), Vector2(half * 0.8, base), Vector2(-half * 0.8, base)]
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
