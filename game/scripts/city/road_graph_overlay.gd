extends Node3D
## Draws what `RoadGraph` thinks is under the car, live (`P2-2`).
##
## A deliverable rather than a nicety. `P2-2` is otherwise a parse and two query
## functions — the only task in the project with nothing to look at — and this
## project's two most valuable findings both came from someone's eye rather than
## from a test: `Q12`'s one-way check, and the transposed spawn basis the user
## caught from the driver's seat after it had survived a full drive.
##
## So it draws the three things a wrong answer shows up in:
##
##   * the resolved edge's centreline, in white — is it the road you are on?
##   * the **nearside lane centre**, in green — the placement target `P2-3`
##     spawns against and `P3-3` will route traffic along. It marks where a car
##     *belongs*, so it stays put on the kerbside lane while you drive around;
##     it is not tracking which lane you are in. There is no runtime lane
##     concept to track — `lanes` is authored config, not published by the
##     source, and nothing routes by it.
##   * the legal travel direction, as a chevron — a red chevron means the car is
##     pointing against the flow of a one-way street.
##
## The readout carries the same facts as text, because a screenshot is how an
## agent reports this and colours alone do not survive that.
##
## Dev-only, like the other previews. Nothing in a shipped scene should read it.

const PreviewDraw = preload("res://scripts/city/preview_draw.gd")

## What the overlay follows. Left empty it takes the first `VehicleController`
## it can find, so dropping the node into a drive scene is enough.
@export var vehicle_path: NodePath = NodePath()

## Lifted clear of the carriageway so it does not z-fight the road surface it is
## drawn on top of. Larger than `road_preview.gd`'s 0.15 m because this is drawn
## over the real ribbon rather than over bare terrain.
@export var lift_m: float = 0.25

## How far to look. Beyond this the overlay reports a miss rather than reaching
## across the region for something irrelevant.
@export var search_radius_m: float = 60.0

@export var show_readout: bool = true

const _CENTRELINE := Color(0.95, 0.95, 0.98)
const _LANE := Color(0.35, 0.90, 0.45)
const _WITH_FLOW := Color(0.35, 0.90, 0.45)
const _AGAINST_FLOW := Color(0.95, 0.30, 0.25)
const _MISS := Color(0.95, 0.65, 0.20)

var _graph: RoadGraph = null
var _vehicle: Node3D = null
var _mesh: MeshInstance3D = null
var _readout: Label = null


func _ready() -> void:
	# One parse for the whole scene. `road_preview.gd` and `fare_preview.gd` in
	# the preview scenes take the same instance from the same accessor.
	_graph = RoadGraph.shared()
	if _graph.is_empty():
		# `GeneratedRoadGraph` has already said what is missing and how to fix it.
		set_physics_process(false)
		return

	_vehicle = get_node_or_null(vehicle_path) as Node3D
	if _vehicle == null:
		var found: Array[Node] = get_tree().get_root().find_children(
			"*", "VehicleController", true, false
		)
		if found.is_empty():
			push_warning("road graph overlay: no vehicle to follow")
			set_physics_process(false)
			return
		_vehicle = found[0] as Node3D

	var material: StandardMaterial3D = PreviewDraw.unshaded_material()
	# Depth test off: the whole point is to see the lane centre through the car
	# and through the kerb it may be sitting behind.
	material.no_depth_test = true
	material.render_priority = 1

	_mesh = MeshInstance3D.new()
	_mesh.name = "GraphOverlay"
	_mesh.material_override = material
	# The overlay draws in world space, so it must not inherit the rig it hangs
	# off. Without this it would be drawn relative to whatever moved last.
	_mesh.top_level = true
	add_child(_mesh)

	if show_readout:
		var layer := CanvasLayer.new()
		layer.name = "GraphReadout"
		_readout = Label.new()
		_readout.position = Vector2(16.0, 96.0)
		_readout.add_theme_color_override("font_color", Color(1, 1, 1))
		_readout.add_theme_color_override("font_outline_color", Color(0, 0, 0))
		_readout.add_theme_constant_override("outline_size", 6)
		layer.add_child(_readout)
		add_child(layer)


func _physics_process(_delta: float) -> void:
	if _graph == null or _vehicle == null or _mesh == null:
		return

	var at: Vector3 = _vehicle.global_position
	# `-Z` is forward in Godot, and taking it from the basis rather than from
	# velocity means the overlay still reports a direction when the car is
	# stationary — which is when someone is most likely to be reading it.
	var heading: Vector3 = -_vehicle.global_transform.basis.z
	var hit: RoadGraph.Hit = _graph.nearest_edge(at, heading, search_radius_m)

	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	if hit.hit():
		_draw_hit(surface, hit, heading)
	else:
		_draw_miss(surface, at)
	_mesh.mesh = surface.commit()

	if _readout != null:
		_readout.text = _describe(hit, at, heading)


func _draw_hit(surface: SurfaceTool, hit: RoadGraph.Hit, heading: Vector3) -> void:
	var centreline: PackedVector3Array = _graph.polyline_of(hit.edge_id)
	for step: int in centreline.size() - 1:
		PreviewDraw.ribbon(
			surface, _lift(centreline[step]), _lift(centreline[step + 1]), 0.35, _CENTRELINE
		)

	# A cross at the lane centre rather than a dot: a dot at this scale is a few
	# pixels in a screenshot, and the whole claim is *where* it is.
	var lane: Vector3 = _lift(hit.lane_centre)
	var side: Vector3 = Vector3.UP.cross(hit.forward).normalized() * 1.1
	var along: Vector3 = hit.forward * 1.1
	PreviewDraw.ribbon(surface, lane - along, lane + along, 0.3, _LANE)
	PreviewDraw.ribbon(surface, lane - side, lane + side, 0.3, _LANE)

	# Chevron along the legal direction, from the lane centre. Red when the car
	# is facing against a one-way flow — the check no test in this repo makes.
	var against: bool = hit.one_way and Vector3(heading.x, 0.0, heading.z).dot(hit.forward) < 0.0
	var colour: Color = _AGAINST_FLOW if against else _WITH_FLOW
	var nose: Vector3 = lane + hit.forward * 5.0
	PreviewDraw.ribbon(surface, lane, nose, 0.5, colour)
	surface.set_color(colour)
	for corner: Vector3 in [nose + hit.forward * 2.0, nose - side * 1.4, nose + side * 1.4]:
		surface.add_vertex(corner)


## A cross where the car is, so "no road here" is visibly drawn rather than
## silently blank — a blank overlay and a broken overlay look identical.
func _draw_miss(surface: SurfaceTool, at: Vector3) -> void:
	var centre: Vector3 = at + Vector3.UP * lift_m
	PreviewDraw.ribbon(
		surface, centre + Vector3(-2.0, 0.0, -2.0), centre + Vector3(2.0, 0.0, 2.0), 0.3, _MISS
	)
	PreviewDraw.ribbon(
		surface, centre + Vector3(-2.0, 0.0, 2.0), centre + Vector3(2.0, 0.0, -2.0), 0.3, _MISS
	)


func _lift(point: Vector3) -> Vector3:
	return Vector3(point.x, point.y + lift_m, point.z)


func _describe(hit: RoadGraph.Hit, at: Vector3, heading: Vector3) -> String:
	if not hit.hit():
		return (
			"road graph: no drivable edge within %.0f m of (%.1f, %.1f)"
			% [search_radius_m, at.x, at.z]
		)

	var road: String = hit.road_name_en if not hit.road_name_en.is_empty() else "(unnamed)"
	# Signed, so the readout says which side of the centreline the car is on
	# rather than only how far. Positive is left of travel, which in Hong Kong
	# is the side a car should be on.
	var left: Vector3 = Vector3.UP.cross(hit.forward).normalized()
	var lateral: float = (at - hit.point).dot(left)
	var side: String = "left" if lateral >= 0.0 else "RIGHT of centreline"
	var flat := Vector3(heading.x, 0.0, heading.z)
	var agreement: float = (
		flat.normalized().dot(hit.forward) if flat.length_squared() > 0.0 else 1.0
	)
	var flow: String = "one-way" if hit.one_way else "two-way"
	var against: String = "  ⚠ AGAINST FLOW" if hit.one_way and agreement < 0.0 else ""
	return (
		"edge %d  %s  (%s, level %d)\n" % [hit.edge_id, road, flow, _graph.level_of(hit.edge_id)]
		+ "car %.2f m %s, t=%.3f\n" % [absf(lateral), side, hit.t]
		+ (
			"nearside lane centre %.2f m off centreline — placement target,\n"
			% hit.lane_centre.distance_to(hit.point)
		)
		+ (
			"  not a lane tracker; car is %.2f m from it\n"
			% RoadGraph.plan_distance(at, hit.lane_centre)
		)
		+ "heading agrees with travel: %+.2f%s" % [agreement, against]
	)
