class_name MenuProfile
extends Resource
## What the start menu is made of (`P6-1`): the hero shots round the parked
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

@export_group("Hero shots")
## Where the camera stands round the parked car on each page (`MenuOrbit`):
## HOME circles it, PLAY looks at it ready to pull away, OPTIONS stands at its
## tail, the sheets (guide, credits, notices) look down on it from over the
## street, and the shift's REPORT faces it head on.
@export var shot_home: MenuShot
@export var shot_play: MenuShot
@export var shot_options: MenuShot
@export var shot_sheet: MenuShot
@export var shot_report: MenuShot
## How fast the camera closes on a new page's shot, per second — the chase
## rig's filter (`ChaseProfile.yaw_response`).
@export var shot_response: float

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

@export_group("Backdrop")
## The blur behind the menu's text (`Q163`, the user's ask): the screen's mip
## level it reads, how wide HOME's side panel is from the screen's left edge,
## and where across that width it starts to fade out.
@export var backdrop_lod: float
@export var backdrop_width_px: float
@export var backdrop_fade_from: float
