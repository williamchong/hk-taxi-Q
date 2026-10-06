class_name LightTail
extends Node3D
## The light tail (`P3-70`, `Q158` reversed on the user's ask, 2026-10-07):
## while a slide counts, each tail lamp leaves a streak along the arc it swings
## through, fading over `life_s`; the body carries only the city's line. The
## tier is `SkillTracker.drift_tier`, the SAME meter that pays, handed in by
## `TaxiHire` off `FareSystem`'s `drift_tier_changed` as the sparks take it —
## a slide the tracker is not counting lights nothing. Under `--fares=off`
## nothing calls `show_tier` and no streak shows.
##
## The lamps are found in the body mesh, not named: the import stamps every
## lens with `MARKER_LAMP` in `UV.y` and its circuit in `UV.x`
## (`generated_scene_import.gd`, the payload `vehicle_body.gdshader` lights), so
## the brake circuit's lenses are the tail lamps. The high-level brake lamp in
## the backlight is left out: it sits on the centreline, and a third streak
## between the two reads as a bar, not a pair of lamps.
##
## ⚠️ **One draw call for the whole tail, however long the drive.** One
## `ArrayMesh` of `capacity` pieces allocated once, each new piece uploaded in
## place — positions and lay times — as `SkidMarks` uploads a mark, and hidden
## once every piece has faded. The clock is its own, summed from the physics
## tick, so the drive harness's replay lays and fades the same tail.
##
## Presentation only: nothing here is read by the physics. On the physics tick,
## after the car's own, so a piece is laid where the tick left the lamp.

const SHADER: Shader = preload("res://assets/shaders/light_tail.gdshader")
## `generated_scene_import.gd`'s stamps: the lamp marker in `UV.y`, the brake
## circuit in `UV.x`. Restated, because the import script is editor-side;
## `verify_vehicle.gd` holds the circuit to the imported body by finding the
## two tail lamps through it.
const MARKER_LAMP: float = 2.0
const CIRCUIT_BRAKE: float = 1.0
## Lens vertices closer to the centreline than this share of the body's half
## width are the high-level brake lamp's.
const CENTRE_SHARE: float = 0.25
## Bytes per corner in a positions-only vertex stream, and in a UV-only
## attribute stream.
const VERTEX_STRIDE: int = 12
const ATTRIBUTE_STRIDE: int = 8

## The tail's dials and colours. Assigned in `taxi_tyre.tscn`; the values and
## their reasons are `tuning/light_tail.md`'s.
@export var profile: LightTailProfile


## One tail lamp's lens in the body mesh's own space: where it is, and its
## half-extents across the car and up.
class Lens:
	var centre: Vector3
	var half_across: Vector3
	var half_up: Vector3


var _body: MeshInstance3D = null
var _lenses: Array[Lens] = []
var _trail: LightTrail = null
var _mesh: ArrayMesh = null
var _streak: MeshInstance3D = null
var _material: ShaderMaterial = null
var _tier: int = -1
var _clock_s: float = 0.0
## When the last piece was laid, so the mesh is hidden once it has faded.
var _laid_at_s: float = -INF


func _ready() -> void:
	set_physics_process(false)
	if not usable():
		return
	# A child is ready before its parent: deferred, so the car and its body are
	# in the tree when the search runs, as the sparks and the marks defer.
	_setup.call_deferred()


func _setup() -> void:
	var car: VehicleController = VehicleController.above(self)
	if car == null:
		push_error("LightTail: not under a VehicleController; no streak will show.")
		return
	# The body is the first mesh in the car, ahead of the door leaf and the
	# wheels — `VehicleLamps`' search, for the same reason: the asset names it.
	var found: Array[Node] = car.find_children("*", "MeshInstance3D", true, false)
	if found.is_empty():
		push_error("LightTail: the car has no mesh; no streak will show.")
		return
	_body = found[0] as MeshInstance3D
	_lenses = lenses_of(_body.mesh)
	if _lenses.size() != 2:
		push_error(
			(
				"LightTail: %d brake lenses off the centreline, not 2; no streak will show."
				% _lenses.size()
			)
		)
		return
	_trail = LightTrail.new(
		_lenses.size(), capacity_for(_lenses.size(), profile.life_s), profile.max_step_m
	)
	if not _build_mesh():
		return
	set_physics_process(true)


## Whether the table is whole: a profile, at least one colour, and no zero
## anywhere — every key has an export floor above zero, so a zero is a missing
## key. Pure over `profile`, so `verify_vehicle.gd` can ask it of a car that
## never entered a tree.
func usable() -> bool:
	if profile == null:
		push_error("LightTail: no LightTailProfile assigned; no streak will show.")
		return false
	var required: Dictionary[String, float] = {
		"colours": float(profile.colours.size()),
		"life_s": profile.life_s,
		"fade_power": profile.fade_power,
		"max_step_m": profile.max_step_m,
		"width_scale": profile.width_scale,
	}
	return not TuningTable.any_zero(profile, required, "LightTail", "no streak will show")


## The tier the tail shows: `SkillTracker.drift_tier`'s -1 stops the streak,
## which then fades on its own; 0 and up lay it in `colours[tier]`, the last
## colour past the end. One colour for the whole ring, so a step up recolours
## the streak already laid — as the sparks already up take the new colour.
func show_tier(tier: int) -> void:
	_tier = tier
	if _material != null and tier >= 0:
		_material.set_shader_parameter(&"colour", colour_of(tier))


## The colour a tier streaks in; clear at -1, so a lit streak is a counted slide.
func colour_of(tier: int) -> Color:
	if tier < 0 or profile == null or profile.colours.is_empty():
		return Color(0.0, 0.0, 0.0, 0.0)
	return profile.colours[mini(tier, profile.colours.size() - 1)]


## How many pieces of streak have been laid since the car was built.
func laid() -> int:
	return _trail.laid if _trail != null else 0


## Pieces enough to hold `life_s` of every lamp at the physics rate, and one
## tick's slack a lamp — so no piece is overwritten before it has faded.
static func capacity_for(lamps: int, life_s: float) -> int:
	return lamps * (ceili(life_s * Engine.physics_ticks_per_second) + 1)


## The tail lamps in `mesh`: the brake circuit's lens vertices off the
## centreline, boxed per side, the side at the negative offset first. The box
## is the body's own: its length runs along its longer horizontal side and
## across is the other. Pure, so `verify_vehicle.gd` can ask it of the
## imported body.
static func lenses_of(mesh: Mesh) -> Array[Lens]:
	var box: AABB = mesh.get_aabb()
	var across: Vector3 = Vector3.BACK if box.size.x > box.size.z else Vector3.RIGHT
	var half_width: float = box.size.dot(across) * 0.5
	var sides: Dictionary[float, AABB] = {}
	for surface: int in mesh.get_surface_count():
		var arrays: Array = mesh.surface_get_arrays(surface)
		var payload: Variant = arrays[Mesh.ARRAY_TEX_UV]
		if typeof(payload) != TYPE_PACKED_VECTOR2_ARRAY:
			continue
		var uvs: PackedVector2Array = payload
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		for i: int in uvs.size():
			if floorf(uvs[i].y) != MARKER_LAMP or floorf(uvs[i].x) != CIRCUIT_BRAKE:
				continue
			var offset: float = (vertices[i] - box.get_center()).dot(across)
			if absf(offset) < half_width * CENTRE_SHARE:
				continue
			var side: float = signf(offset)
			if sides.has(side):
				sides[side] = sides[side].expand(vertices[i])
			else:
				sides[side] = AABB(vertices[i], Vector3.ZERO)
	var lenses: Array[Lens] = []
	var order: Array[float] = sides.keys()
	order.sort()
	for side: float in order:
		var lens := Lens.new()
		var extent: AABB = sides[side]
		lens.centre = extent.get_center()
		lens.half_across = across * extent.size.dot(across) * 0.5
		lens.half_up = Vector3.UP * extent.size.y * 0.5
		lenses.append(lens)
	return lenses


func _physics_process(delta: float) -> void:
	_clock_s += delta
	var frame: Transform3D = _body.global_transform
	for k: int in _lenses.size():
		var lens: Lens = _lenses[k]
		var slot: int = _trail.step(
			k,
			_clock_s,
			frame * lens.centre,
			frame.basis * lens.half_across * profile.width_scale,
			frame.basis * lens.half_up * profile.width_scale,
			_tier >= 0
		)
		if slot >= 0:
			_upload(slot)
			_laid_at_s = _clock_s
	# Hidden once every piece has faded, so a car that is not sliding costs no
	# draw and no uniform write.
	var showing: bool = _clock_s - _laid_at_s < profile.life_s
	_streak.visible = showing
	if showing:
		_material.set_shader_parameter(&"now_s", _clock_s)


## The ring, empty: every corner at the origin, laid at time zero. Refuses a
## renderer whose streams are not the bytes a corner `_upload` writes.
func _build_mesh() -> bool:
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = _trail.positions()
	arrays[Mesh.ARRAY_TEX_UV] = _trail.times()
	arrays[Mesh.ARRAY_INDEX] = _trail.indices()
	_mesh = ArrayMesh.new()
	_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var corners: int = _trail.positions().size()
	var format: int = _mesh.surface_get_format(0)
	var vertex_stride: int = RenderingServer.mesh_surface_get_format_vertex_stride(format, corners)
	var attribute_stride: int = RenderingServer.mesh_surface_get_format_attribute_stride(
		format, corners
	)
	if vertex_stride != VERTEX_STRIDE or attribute_stride != ATTRIBUTE_STRIDE:
		push_error(
			(
				"LightTail: the renderer's strides are %d and %d bytes, not %d and %d; no streak will show."
				% [vertex_stride, attribute_stride, VERTEX_STRIDE, ATTRIBUTE_STRIDE]
			)
		)
		return false
	# The streak is wherever the car has been: never culled by the ring's
	# bounds at build time, which are a point.
	_mesh.custom_aabb = AABB(Vector3(-1.0e5, -1.0e3, -1.0e5), Vector3(2.0e5, 2.0e3, 2.0e5))
	_material = ShaderMaterial.new()
	_material.shader = SHADER
	_material.set_shader_parameter(&"life_s", profile.life_s)
	_material.set_shader_parameter(&"fade_power", profile.fade_power)
	_material.set_shader_parameter(&"colour", colour_of(maxi(_tier, 0)))
	_mesh.surface_set_material(0, _material)
	_streak = MeshInstance3D.new()
	_streak.name = "Streak"
	_streak.mesh = _mesh
	_streak.top_level = true
	_streak.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_streak.visible = false
	add_child(_streak)
	_streak.global_transform = Transform3D.IDENTITY
	return true


## Writes the corners of `slot` into the mesh in place: their positions, and
## when they were laid.
func _upload(slot: int) -> void:
	var first: int = slot * LightTrail.CORNERS
	var last: int = first + LightTrail.CORNERS
	var rid: RID = _mesh.get_rid()
	RenderingServer.mesh_surface_update_vertex_region(
		rid, 0, first * VERTEX_STRIDE, _trail.positions().slice(first, last).to_byte_array()
	)
	RenderingServer.mesh_surface_update_attribute_region(
		rid, 0, first * ATTRIBUTE_STRIDE, _trail.times().slice(first, last).to_byte_array()
	)
