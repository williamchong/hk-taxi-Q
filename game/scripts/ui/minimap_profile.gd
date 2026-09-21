class_name MinimapProfile
extends Resource
## How much city the minimap shows, and which way up (`P3-44`, `Q136`).
## Rationale in `tuning/minimap.md`; the colours are `HudStyle`'s.
##
## 🔴 **No `@export` here declares a default**, on `HudStyle`'s convention;
## `verify_hud.gd` refuses a zero by name.

## Path to the shipped table, so `hud.gd` and `verify_hud.gd` cannot load two
## different files.
const PATH: String = "res://tuning/minimap.tres"

## Metres of city across the slot's WIDTH. The scale is derived from this and
## the slot, so resizing the slot in `hud_layout.tres` shows the same streets
## larger rather than more streets at the same size.
@export var span_m: float

## True turns the map so the car's nose is up; false pins north up.
@export var heading_up: bool

## Where the car sits in the slot, as a fraction of it. Below the middle under
## `heading_up`, because the road ahead is what the glance is for.
@export var anchor: Vector2

## The narrowest a road may draw, in design pixels. An alley at its own width
## is under a pixel at this scale and would flicker out as the map turns.
@export var min_stroke_px: float

## How far a deck's casing stands proud of the deck each side, in design pixels
## — what makes a flyover read as OVER the street it crosses.
@export var casing_px: float

## The one-way arrows (`Q136`): an arrowhead this long, in design pixels, about
## every `arrow_spacing_px` along a one-way road. `arrow_px` 0 draws none.
@export var arrow_px: float
@export var arrow_spacing_px: float

## The car's chevron, tip to tail, in design pixels.
@export var marker_px: float
