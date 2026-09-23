class_name HudStyle
extends Resource
## What the HUD is made of (`P3-24`) — one palette, one shape, one type scale.
##
## **One voice: the 的士咪錶 (`Q139`, the user's call).** Every panel is the
## meter's black housing under one bezel keyline, lettering is light, and the
## cab's two instruments keep their own faces: the dashboard's dial for the
## speed, the meter's red seven-segment LED for the fare (`P3-5a`).
## `ART_DESIGN.md` always named the taxi meter as half this HUD's language;
## until `Q139` only the signage half was drawn, as `Q80`'s "white is the city
## speaking, dark is the car speaking" — two voices, which read as two designs
## once the map made the white half the larger one.
##
## 🔴 **This table IS the theme, and a car may name its own.** A Crown Comfort
## gets this meter; a Comfort Hybrid would get a modern cluster as a second
## `.tres` of this class. Nothing selects one yet because there is one car —
## `Hud` loads `PATH` — and the seam is here: keep every look in this table and
## out of `hud.gd`, or the second theme becomes a code fork.
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

# ---- the housing, and the street name on it ----

## The housing: the field of every panel. `chip_field` and `map_field` must
## equal it — three keys because three panels read them, one value because it
## is one housing, and `verify_hud.gd` holds them together. 🔴 Opaque: the map
## is clipped by this colour's drawn alpha (`minimap.gd`).
@export var plate_field: Color
@export var plate_ink: Color
## The bezel: one keyline round every panel, and the rule over the name strip.
@export var plate_edge: Color
@export var plate_size_en: int
@export var plate_size_zh: int
## Ink-to-edge padding on the plate, which is cut to its text rather than
## drawn at a fixed width. See `hud.gd::_fit_plate`.
@export var plate_pad: Vector2

# ---- instruments ----

## The housing again — see `plate_field`.
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

## The dashboard's dial round the numerals (`speed_dial.gd`): where the scale
## ends, the two tick spacings, the ticks' weight, the needle, and how far the
## dial stands in from the chip's edge. Ticks draw in `chip_muted`.
##
## ⚠️ `dial_full_scale_kph` is a DIAL's, not the car's: `handling.tres` tops
## out at 140 and a speedometer that ends where the car does never looks fast.
## 🔴 The needle is amber and `verify_hud.gd` holds it off red — red is the
## fare's (the user's call), and the bar's red already means "losing speed".
@export var dial_full_scale_kph: float
@export var dial_major_kph: float
@export var dial_minor_kph: float
@export var dial_tick_px: float
@export var dial_inset_px: float
@export var dial_needle: Color
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

## The sign's white — the world sign's `#f0f0ea`. Its own key since `Q139`: it
## borrowed the plate's white while the plate had one.
@export var warn_bar: Color

## Flashes per second while the sign is up.
##
## 🔴 **Capped, and the cap is not a taste.** Above three flashes per second is
## the photosensitive-seizure threshold in WCAG 2.3.1, and an arcade alarm has no
## reason to go near it — two reads as urgent and stays well clear.
## `verify_hud.gd` refuses a faster one.
@export var warn_blink_hz: float

# ---- the minimap ----

## The map's ground: the housing (see `plate_field`).
##
## 🔴 **Opaque, and `verify_hud.gd` refuses anything else**, for two reasons that
## are both invisible until they are not: `minimap.gd` clips the roads by this
## panel's drawn ALPHA, and a deck's casing is this colour drawn over the street
## beneath it, which only hides the street if nothing shows through.
@export var map_field: Color
## The roads. Light on the housing, a figure-ground plan: a street is a few
## pixels wide and wants the most contrast the palette has.
## 🔴 **Opaque too**: strokes overlap at every joint (`minimap_mesh.gd`).
@export var map_road: Color
## A main road (`RoadGraph.is_main`) — lighter than `map_road`, opaque for the
## same reason.
@export var map_road_main: Color
## The car's chevron and its rim: taxi red, the one saturated thing on the map. Not the bar's green, which already means "gaining".
@export var map_marker: Color
@export var map_marker_edge: Color

# ---- dev only ----

## The reserved slots' outline, drawn only under `DebugHud`'s FULL view.
## The 咪錶's face (`P3-5a`): red LED digits over their ghosts, the fare in
## dollars to one place in `meter_cells` cells.
@export var meter_lit: Color
@export var meter_unlit: Color
@export var meter_digit_px: float
@export var meter_segment_px: float
@export var meter_slant: float
@export var meter_cells: int
@export var meter_label_size: int
## The tip clock: seconds left on the allowance, red under `timer_warn_s`.
@export var timer_size: int
@export var timer_unit_size: int
@export var timer_unit_gap: int
@export var timer_warn_s: float
@export var timer_outline_px: int
## The bilingual callout: the nearest pickup or the destination, and the
## outcome of a fare held for `callout_hold_s` after it ends.
@export var callout_caption_size: int
@export var callout_size_en: int
@export var callout_size_zh: int
@export var callout_sub_size: int
## The Chinese face is a Kai whose strokes thin out at the Latin sizes, so
## its caption and road line are set larger (the user's call: unreadable).
@export var callout_caption_size_zh: int
@export var callout_sub_size_zh: int
## The gap between the callout's three lines, per language: the Kai wants air.
@export var callout_line_gap: int
@export var callout_line_gap_zh: int
@export var callout_hold_s: float
## The meter's tick flash under the clock: its size and how long it fades.
@export var tick_size: int
@export var tick_fade_s: float
## The map's pins: every pending customer at `map_pending_px`, and the one
## destination at `map_pin_px`.
@export var map_pickup: Color
@export var map_destination: Color
@export var map_pending_px: float
@export var map_pin_px: float
## The target's arrow on the map's border while it is off the map, tip to tail.
@export var map_beacon_px: float
@export var slot_fill: Color
@export var slot_edge: Color
