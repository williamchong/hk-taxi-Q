class_name HudStyle
extends Resource
## What the HUD is made of (`P3-24`) — one palette, one shape, one type scale.
##
## **The rule that makes this feel like one thing: white is the city speaking,
## dark is the car speaking.** The street plate is a *sign* — it quotes the
## white-field, black-ink street name plates bolted to Wan Chai's buildings, and
## it tells you where you are. The speed is an *instrument* — dark chip, light
## numerals, one saturated accent — and it tells you what the car is doing.
## Two readouts, two voices, and the palette is what says which is which.
##

## ⚠️ **These are NOT the road's paint colours, deliberately.**
## `roadmarks.tres` records that the marking white is already its **fifth**
## authored copy and `boxjunctions.tres` that the yellow is its **third**, with
## `Q53` predicting each new one. Adding a sixth and a fourth here would be that
## debt again — and it would be wrong on the merits: a street name plate is not
## paint, and if the carriageway's white is ever re-graded the sign bolted to a
## building has no reason to follow. The UI palette is chosen to *sit with* the
## road's and is its own to move.
##
## ⚠️ **Data, per hard rule 4**, and unlike `debug_hud.gd`'s constants this one
## earns it: `P3-5b`'s whole deliverable is tuning the HUD's look, and the
## timer, meter and minimap will draw from this table without touching code.

## Path to the shipped table, so `hud.gd` and `verify_hud.gd` cannot load two
## different files.
const PATH: String = "res://tuning/hud_style.tres"

# ---- the shape ----

## The corner cut on every panel. The UI's single geometric idea, echoing the
## faceted, hard-normal geometry of everything behind it.
@export var chamfer_px: float = 14.0
@export var edge_px: float = 3.0
## The reserved slots' outline, thinner than a live panel's.
@export var slot_edge_px: float = 2.0

# ---- the city's voice: the street name plate ----

## A sign white. Near the carriageway's marking white and independent of it.
@export var plate_field: Color = Color(0.93, 0.93, 0.90)
@export var plate_ink: Color = Color(0.07, 0.07, 0.08)
## A hard black keyline, not a soft grey border. Real plates have a printed
## rule around them and a 1 px neutral stroke is what made this read as a dialog.
@export var plate_edge: Color = Color(0.07, 0.07, 0.08)
@export var plate_size_en: int = 26
@export var plate_size_zh: int = 30
## Ink-to-edge padding on the plate, which is cut to its text rather than
## drawn at a fixed width. See `hud.gd::_fit_plate`.
@export var plate_pad: Vector2 = Vector2(34.0, 14.0)

# ---- the car's voice: instruments ----

## Darker than `asphalt_aged` (`#42403d`) on purpose. The chip sits *on* the
## road, and matching the road exactly would make it disappear into it at
## exactly the moment the player glances down.
@export var chip_field: Color = Color(0.14, 0.135, 0.128, 0.88)
@export var chip_ink: Color = Color(0.96, 0.96, 0.94)
@export var chip_muted: Color = Color(0.70, 0.69, 0.65)

## The one saturated colour, in the family of Hong Kong's box-junction yellow.
## Used as a single bar along the bottom of an instrument and nowhere else —
## `ART_DESIGN.md` says the saturated accents are accents, and a HUD is where
## that discipline is easiest to lose.
##
## ⚠️ **Taxi red is deliberately NOT here.** It is the player's own car and the
## one non-negotiable colour in the anchor table; spending it on HUD furniture
## now leaves `P3-5a` nothing to say "fare" with.
@export var accent: Color = Color(0.86, 0.68, 0.13)
## What the bar reads when the car is losing speed. Cool and unsaturated against
## the accent's warmth — braking is not a smaller version of accelerating.
##
## ⚠️ **Not red.** Taxi red is the car's own and `P3-5a`'s to spend, and a red
## bar on a speedometer also reads as a warning, which losing speed is not.
@export var accent_negative: Color = Color(0.45, 0.62, 0.78)
## The unlit bed. A reading of zero must look like zero rather than like a panel
## that has stopped drawing.
@export var accent_track: Color = Color(1.0, 1.0, 1.0, 0.12)
@export var accent_px: float = 5.0

## Longitudinal acceleration, in m/s², at which the bar is hard over.
##
## Measured off `drive.sh` telemetry on the shipped car rather than guessed:
## 45.6 → 54.8 kph in one second is 2.55 m/s², 67.5 → 79.5 is 3.34, and the
## first second off the line is steeper than either. 5.0 puts ordinary
## acceleration across most of the bed and leaves headroom before it pegs.
@export var accel_full_scale_mps2: float = 5.0

## How quickly the bar follows. A physics velocity differentiated per frame is
## far too noisy to read; this is the time constant of the filter over it.
@export var accel_smoothing_s: float = 0.18

@export var speed_size: int = 104
@export var speed_unit_size: int = 30
## Pulls `km/h` up under the numerals, which carry far more leading than
## they need at this size.
@export var speed_line_tighten: int = -18

# ---- dev only ----

## The reserved slots' outline, drawn only under `DebugHud`'s FULL view.
@export var slot_fill: Color = Color(0.30, 0.85, 0.95, 0.10)
@export var slot_edge: Color = Color(0.30, 0.85, 0.95, 0.55)
