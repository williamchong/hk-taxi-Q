class_name MenuProfile
extends Resource
## What the start menu is made of (`P6-1`): the hero orbit round the parked
## taxi, the column's geometry and the type scale.
##
## Colours and the panel shape are NOT here: they are `HudStyle`'s, so the menu
## is drawn in the cab's one housing (`Q139`) and a second theme for a second
## car re-skins both at once.
##
## 🔴 **No `@export` here declares a default**, on `HudStyle`'s convention: a
## default is a second copy of the tuning table, and a second copy drifts.
## `verify_menu.gd` refuses a zero it would draw with.

## Path to the shipped table, so `start_menu.gd`, `menu_orbit.gd` and
## `verify_menu.gd` cannot load two different files.
const PATH: String = "res://tuning/menu.tres"

@export_group("Hero orbit")
## The spring arm's length while the menu is up, and the pivot's height over
## the car's origin; the chase rig's own numbers come back on start.
@export var orbit_distance_m: float
@export var orbit_height_m: float
@export var orbit_pitch_deg: float
## One full circle round the car takes this long.
@export var orbit_period_s: float
## Where the circle starts, in degrees from the car's own heading.
@export var orbit_start_deg: float
@export var orbit_fov_deg: float

@export_group("Layout")
## The column's inset from the safe area's bottom-left corner.
@export var margin_px: Vector2
@export var button_px: Vector2
@export var button_gap_px: int
## The credits panel, centred, and the padding inside its keyline.
@export var credits_px: Vector2
@export var credits_pad_px: int
## The guide sheet, centred, and each step's drawn picture.
@export var guide_px: Vector2
@export var guide_picture_px: Vector2

@export_group("Type")
@export var title_size: int
@export var subtitle_size: int
@export var subtitle_size_zh: int
@export var button_size: int
@export var button_size_zh: int
@export var heading_size: int
@export var heading_size_zh: int
@export var body_size: int
@export var body_size_zh: int
