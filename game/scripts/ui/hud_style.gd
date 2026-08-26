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
##
## 🔴 **No `@export` here declares a default**, on `HandlingProfile`'s and
## `StreamingProfile`'s convention: a default is a second copy of the tuning
## table, and a second copy drifts. This file's did — it still named a 104 px
## numeral while the shipped `.tres` drew 68.

## Path to the shipped table, so `hud.gd` and `verify_hud.gd` cannot load two
## different files.
const PATH: String = "res://tuning/hud_style.tres"

# ---- the shape ----

## The corner cut on every panel. The UI's single geometric idea, echoing the
## faceted, hard-normal geometry of everything behind it.
@export var chamfer_px: float
@export var edge_px: float
## The reserved slots' outline, thinner than a live panel's.
@export var slot_edge_px: float

# ---- the city's voice: the street name plate ----

## A sign white. Near the carriageway's marking white and independent of it.
@export var plate_field: Color
@export var plate_ink: Color
## A hard black keyline, not a soft grey border. Real plates have a printed
## rule around them and a 1 px neutral stroke is what made this read as a dialog.
@export var plate_edge: Color
@export var plate_size_en: int
@export var plate_size_zh: int
## Ink-to-edge padding on the plate, which is cut to its text rather than
## drawn at a fixed width. See `hud.gd::_fit_plate`.
@export var plate_pad: Vector2

# ---- the car's voice: instruments ----

## Darker than `asphalt_aged` (`#42403d`) on purpose. The chip sits *on* the
## road, and matching the road exactly would make it disappear into it at
## exactly the moment the player glances down.
@export var chip_field: Color
@export var chip_ink: Color
@export var chip_muted: Color

## The bar's two readings: **green for gaining speed, red for losing it.**
##
## 🔴 **The convention beat the palette argument, and it should have.** These
## were the box-junction yellow and a cool blue, chosen so that no HUD furniture
## spent the taxi's red. But green-is-go and red-is-stop is the oldest
## convention a driver has — it is the traffic signal and it is the car's own
## brake lamps — and a bar that a driver has to *learn* is a bar that is not
## doing its job. The red here is not the taxi's body colour being spent on
## decoration; it is red used for the one thing red means.
##
## ⚠️ **Kept clear of the vehicle palette on both sides.** This green is brighter
## and cooler than `ART_DESIGN.md`'s deep vegetation green and the minibus roof,
## and this red is hotter and lighter than the taxi body, so neither reads as an
## object that has escaped the world into the HUD.
@export var accent: Color
@export var accent_negative: Color
## The unlit bed. A reading of zero must look like zero rather than like a panel
## that has stopped drawing.
@export var accent_track: Color
@export var accent_px: float

## Longitudinal acceleration, in m/s², at which the bar is hard over.
##
## Measured off `drive.sh` telemetry on the shipped car rather than guessed:
## 45.6 → 54.8 kph in one second is 2.55 m/s², 67.5 → 79.5 is 3.34, and the
## first second off the line is steeper than either. 5.0 puts ordinary
## acceleration across most of the bed and leaves headroom before it pegs.
@export var accel_full_scale_mps2: float

## How quickly the bar follows. A physics velocity differentiated per frame is
## far too noisy to read; this is the time constant of the filter over it.
@export var accel_smoothing_s: float

@export var speed_size: int
@export var speed_unit_size: int
## Pulls `km/h` up under the numerals, which carry far more leading than
## they need at this size.
@export var speed_line_tighten: int

# ---- the city answering back: the wrong-way sign ----

## The NO ENTRY disc drawn when the car is going the wrong way down a one-way
## street, and its bar's two proportions.
##
## 🔴 **These are the WORLD sign's numbers, and the duplication is deliberate and
## declared.** `hong_kong.yaml` gives `TS115` a red disc at `size: 1.00` with a
## white bar at `0.87`, and `signs.py::_NO_ENTRY_BAR_THICKNESS` gives the bar
## `0.187` — both **measured** off TD's own cell by `sign_face_survey.py`, not
## authored, after `Q67` found this project had drawn them 0.66 by 0.22 for a
## year. Those files are build-time and are not reachable from `res://`, so the
## HUD keeps its own copy and `verify_hud.gd` fails when the two disagree.
##
## ⚠️ **This is the one place the UI palette deliberately DOES quote the world**,
## against the rule at the top of this file. That rule is about the road's
## *paint* — the marking white and the box-junction yellow, `Q53`'s fifth and
## third copies — and its reason is that a plate bolted to a building has no
## business following a re-graded carriageway. This is the opposite case: the
## icon's whole argument is that it is the same sign the player has been driving
## past, and a HUD NO ENTRY in some other red would be a worse sign, not a purer
## palette.
@export var warn_disc: Color
@export var warn_bar_length: float
@export var warn_bar_thickness: float

# ⚠️ **The bar has no colour of its own: it draws in `plate_field`.** The city's
# white is already declared once in this table, the sign's `#f0f0ea` and the
# plate's are imperceptibly apart, and a fourth transcribed constant to say so
# would be the debt above with nothing bought for it.

## Flashes per second while the sign is up.
##
## 🔴 **Capped, and the cap is not a taste.** Above three flashes per second is
## the photosensitive-seizure threshold in WCAG 2.3.1, and an arcade alarm has no
## reason to go near it — two reads as urgent and stays well clear.
## `verify_hud.gd` refuses a faster one.
@export var warn_blink_hz: float

# ---- dev only ----

## The reserved slots' outline, drawn only under `DebugHud`'s FULL view.
@export var slot_fill: Color
@export var slot_edge: Color
