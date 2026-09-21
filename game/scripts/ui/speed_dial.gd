class_name SpeedDial
extends Control
## The dashboard's speedometer: an arc of ticks and a needle (`Q139`).
##
## **A cab has two instruments and this is the other one.** The 咪錶 shows the
## fare, in red LED (`seven_segment.gd`, `P3-5a`'s); the speed was never on it.
## Speed is the dashboard's — white ticks on black and an amber needle, which is
## a Crown Comfort's cluster — and the numerals the HUD sets inside the arc are
## printed, not lit, for the same reason.
##
## Built like the minimap: the ticks are one static mesh, the needle is a
## polygon that only ever ROTATES, so a moving needle redraws nothing.

## Where zero sits and how far full scale swings from it, in degrees clockwise
## from "east". An arc over the top, open at the bottom where the numerals'
## unit sits — the shape of the dial it quotes, not a number to tune.
const START_DEG: float = 160.0
const SWEEP_DEG: float = 220.0

## Tick lengths as shares of the radius, and how far in the needle reaches.
const MAJOR_LEN: float = 0.2
const MINOR_LEN: float = 0.11
const NEEDLE_LEN: float = 0.34

## The reading at the end of the scale, and the two tick spacings, in kph.
## ⚠️ All six are read when the dial is built, which is on entering the tree
## and on a resize: set them BEFORE `add_child`, as `hud.gd` does.
@export var full_scale_kph: float
@export var major_kph: float
@export var minor_kph: float
@export var tick_px: float
@export var ink: Color
@export var needle: Color

var _ticks: ArrayMesh = null
var _needle: Polygon2D = null
var _built_for: Vector2 = Vector2.INF


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_needle = Polygon2D.new()
	_needle.name = "Needle"
	_needle.color = needle
	add_child(_needle)
	resized.connect(_rebuild)
	_rebuild()


func _draw() -> void:
	if _ticks != null:
		draw_mesh(_ticks, null)


## Point the needle at `kph`. Reverse reads on the same scale: a needle has no
## minus, and the numerals say `R`.
func show_kph(kph: float) -> void:
	if _needle != null:
		_needle.rotation = deg_to_rad(angle_deg(absf(kph), full_scale_kph))


## The needle's angle for a reading, clamped to the scale's two ends.
static func angle_deg(kph: float, full_scale: float) -> float:
	return START_DEG + SWEEP_DEG * clampf(kph / maxf(full_scale, 0.001), 0.0, 1.0)


## The pivot and radius a dial takes in `box`: as large as fits with the pivot
## low, since the arc is over the top.
static func frame(box: Vector2) -> Vector3:
	var radius: float = minf(box.x * 0.5, box.y * 0.78)
	return Vector3(box.x * 0.5, radius, radius)


func _rebuild() -> void:
	if size == _built_for or _needle == null:
		return
	_built_for = size
	var placed: Vector3 = frame(size)
	var pivot := Vector2(placed.x, placed.y)
	var radius: float = placed.z

	var vertices := PackedVector2Array()
	var count: int = floori(full_scale_kph / maxf(minor_kph, 0.001))
	for step: int in count + 1:
		var kph: float = step * minor_kph
		var major: bool = is_zero_approx(fmod(kph, major_kph))
		var along := Vector2.from_angle(deg_to_rad(angle_deg(kph, full_scale_kph)))
		var across: Vector2 = along.orthogonal() * tick_px * (0.5 if major else 0.3)
		var outer: Vector2 = pivot + along * radius
		var inner: Vector2 = pivot + along * radius * (1.0 - (MAJOR_LEN if major else MINOR_LEN))
		vertices.append_array(
			[
				outer - across,
				outer + across,
				inner + across,
				outer - across,
				inner + across,
				inner - across
			]
		)
	var colours := PackedColorArray()
	colours.resize(vertices.size())
	colours.fill(ink)
	_ticks = CanvasMesh.of(vertices, colours)

	# A wedge on the rim, pointing out along +X at rotation 0: it reaches in
	# only as far as the ticks do, so the middle stays free for the numerals.
	_needle.position = pivot
	_needle.polygon = PackedVector2Array(
		[
			Vector2(radius * 1.02, 0.0),
			Vector2(radius * (1.0 - NEEDLE_LEN), tick_px),
			Vector2(radius * (1.0 - NEEDLE_LEN), -tick_px),
		]
	)
	show_kph(0.0)
	queue_redraw()
