class_name SignalPlanProfile
extends Resource
## How long each part of a signalled junction's cycle lasts (`P3-3b`, `Q173`).
## The rationale for each value is in `tuning/signal_plan.md`; what each *is* is
## here.
##
## 🔴 **Authored, every one**: TD publishes no stage plan and no timings. The
## stages themselves come from the ETL (`signals_plan.json`); this is only how
## long the controller holds each.
##
## 🔴 **No `@export` here declares a default**, on `HudStyle`'s convention: a
## missing key reads as zero, and `SignalController` refuses to run on a zero
## rather than fall back to a literal.

## Path to the shipped table, so the controller and `verify_signals.gd` cannot
## load two different files.
const PATH: String = "res://tuning/signal_plan.tres"

## Red and amber together before a green, in seconds.
@export var red_amber_s: float
## A stage's green, in seconds.
@export var green_s: float
## Amber after a green, in seconds.
@export var amber_s: float
## Every approach red between two stages, in seconds.
@export var all_red_s: float
## A one-axis junction's crossing stage: every approach red, in seconds.
@export var crossing_s: float
