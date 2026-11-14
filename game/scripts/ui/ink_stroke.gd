class_name InkStroke
extends Control
## One stroke of a loaded brush across its own rect, drawn: pressed in at the
## left, drawn right and lifted, the bristles parting into dry streaks at the
## tail. The menu's highlight and the rule under the game's name — the city's
## ink outline (`Q158`) carried into the interface.
##
## Drawn, never a texture: the bundle ships no UI textures (`guide_card.gd`).
## The edge's wobble is a hash of `seed_value`, so a stroke is the same stroke
## every frame and two strokes are two hands.

## Points along each edge.
const STEPS: int = 28
## The dry streaks the tail parts into.
const BRISTLES: int = 4

var ink: Color = Color.WHITE:
	set(value):
		ink = value
		queue_redraw()
var seed_value: int = 0
## How far the stroke climbs left to right, as a share of its height.
var rise: float = 0.18


func _init() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _draw() -> void:
	if size.x <= 0.0 or size.y <= 0.0 or ink.a <= 0.0:
		return
	# The body ends where the bristles begin.
	var body: float = size.x * 0.8
	var top := PackedVector2Array()
	var bottom := PackedVector2Array()
	for step: int in STEPS + 1:
		var t: float = float(step) / STEPS
		var half: float = size.y * 0.5 * _width(t)
		var mid: float = size.y * (0.5 + rise * (0.5 - t))
		top.append(Vector2(body * t, mid - half * (1.0 + 0.16 * _noise(step))))
		bottom.append(Vector2(body * t, mid + half * (1.0 + 0.16 * _noise(step + 97))))
	bottom.reverse()
	draw_colored_polygon(top + bottom, ink)
	# The tail: each bristle its own taper off the body's end, ending ragged.
	var end_mid: float = size.y * (0.5 - rise * 0.5)
	var end_half: float = size.y * 0.5 * _width(1.0)
	for bristle: int in BRISTLES:
		var share: float = (bristle + 0.5) / BRISTLES
		var y: float = end_mid + end_half * (share * 2.0 - 1.0)
		var thick: float = end_half / BRISTLES * (0.55 + 0.35 * absf(_noise(bristle + 211)))
		var reach: float = body + (size.x - body) * (0.45 + 0.55 * absf(_noise(bristle + 307)))
		var lift: float = size.y * rise * 0.2
		draw_colored_polygon(
			PackedVector2Array(
				[
					Vector2(body - 2.0, y - thick),
					Vector2(reach, y - lift - thick * 0.15),
					Vector2(reach, y - lift + thick * 0.15),
					Vector2(body - 2.0, y + thick),
				]
			),
			ink
		)


## The stroke's half-width along it, 0..1: the press, the full belly, the lift.
func _width(t: float) -> float:
	var press: float = smoothstep(0.0, 0.07, t)
	return press * lerpf(1.0, 0.62, t * t)


## A fixed wobble in -1..1 for edge point `index`.
func _noise(index: int) -> float:
	return fposmod(sin(float(index * 131 + seed_value * 977) * 12.9898) * 43758.5453, 2.0) - 1.0
