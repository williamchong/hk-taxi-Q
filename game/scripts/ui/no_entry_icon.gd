class_name NoEntryIcon
extends Control
## The wrong-way warning, drawn as the sign it actually is (`P3-25`).
##
## A red disc with one white bar: **NO ENTRY, `TS115`** — the commonest traffic
## sign code in the region by a wide margin — **179 plates** of it, on poles the
## player has been driving past all game. It is the literal instruction rather
## than a symbol for one, and it needs no lettering, which means it needs no
## typeface, no translation and no `tools/font_coverage.py` entry. ⚠️ That last
## one is not a nicety: `font_coverage.py` grades the street names in
## `roadgraph.json` and would not see a hand-authored HUD string at all, so a
## worded warning would have been ungraded lettering — one character away from
## `Q79`'s tofu box, in a project whose second city is the business case.
##
## 🔴 **A disc, in a UI whose every panel is a cut polygon — and the rule is not
## being broken.** `Q80` settled that the HUD is flat-shaded too: one fill, one
## hard keyline, corners cut, no radius. That rule governs *furniture*. This is
## not furniture, it is **signage**, and the distinction is already load-bearing
## in this palette — `hud_style.gd`'s rule is *white is the city speaking, dark
## is the car speaking*, and the street plate is the city's other voice. A sign
## keeps the shape its publisher draws it in; a HUD panel keeps ours. There is
## deliberately no panel behind this, so nothing here is furniture at all.
##
## ⚠️ **The two proportions are measured, not authored, and they are a THIRD
## copy.** `Q67` rasterised TD's own cell for `TS115` and found the bar spans
## **0.868** of the diameter and is **0.187** thick, against the 0.66 by 0.22
## this project had authored by eye — a quarter short and a sixth too thick, on
## the face the player sees most often. The world sign draws them from
## `hong_kong.yaml` and `signs.py::_NO_ENTRY_BAR_THICKNESS`, which are build-time
## and not readable from `res://`, so the HUD carries its own copy in
## `hud_style.tres`. That is `Q53`'s duplication, knowingly taken — and
## `verify_hud.gd` is the ratchet that fails when the two stop agreeing, because
## a HUD sign drawn to different proportions than the one on the pole is exactly
## the defect `Q67` proved nobody can see.

## The sign's field. The prohibitory red, matched to the world sign's livery.
@export var disc: Color:
	set(value):
		disc = value
		queue_redraw()

## The bar across it. The city's white, and the plate's — see `hud_style.tres`.
@export var bar: Color:
	set(value):
		bar = value
		queue_redraw()

## Bar length as a fraction of the disc's diameter.
@export var bar_length: float:
	set(value):
		bar_length = value
		queue_redraw()

## Bar thickness as a fraction of the disc's diameter.
@export var bar_thickness: float:
	set(value):
		bar_thickness = value
		queue_redraw()


func _ready() -> void:
	# Nothing in this HUD is interactive, and a Control that swallows clicks is
	# how a HUD breaks the touch input it was supposed to be leaving room for.
	# `chamfer_panel.gd` sets it for the same reason and says so at more length.
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _draw() -> void:
	var box: Vector2 = size
	# ⚠️ **The smaller side, so a rect that is not square cannot draw an
	# ellipse.** A squashed NO ENTRY is still legible and still wrong, which is
	# the class of defect this whole file is careful about.
	var radius: float = minf(box.x, box.y) * 0.5
	if radius <= 0.0:
		return
	draw_circle(box * 0.5, radius, disc, true, -1.0, true)
	draw_rect(bar_rect(box, bar_length, bar_thickness), bar)


## The white bar, centred on the disc.
##
## `static` and taking its box explicitly so `verify_hud.gd` can grade the
## geometry with no viewport and no node — `AccentBar.bar_span`'s precedent, and
## for its reason: what can be wrong here is a proportion, and a bar drawn to the
## wrong proportion renders exactly as cleanly as one drawn right.
static func bar_rect(box: Vector2, length: float, thickness: float) -> Rect2:
	var diameter: float = minf(box.x, box.y)
	var span := Vector2(diameter * length, diameter * thickness)
	return Rect2((box - span) * 0.5, span)
