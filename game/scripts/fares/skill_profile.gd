class_name SkillProfile
extends Resource
## The skill bonuses' bars, dwells and prices (`P3-49`, `Q145`): what each
## number *is*. Why each has the value it has is `tuning/skills.md` beside the
## `.tres`. The drift's ANGLE is not here — it is `HandlingProfile`'s
## `drift_slip_threshold_deg`, the one design target the skidpad grades dwell
## against (`Q84`), and a second copy of it would let the two drift apart.
##
## 🔴 **No `@export` here declares a default**, on `FareProfile`'s convention:
## a default is a second copy of the tuning table, and a second copy drifts. A
## missing key reads as zero, and `FareSystem` refuses to run on a zero dwell,
## bar or price rather than fall back to a literal.

## Path to the shipped table, so `fare_system.gd` and `verify_fares.gd` cannot
## load two different files.
const PATH: String = "res://tuning/skills.tres"

## How long a slide must hold at or over the drift threshold before it pays,
## in seconds — and how much longer before it pays again.
@export var drift_s: float
## What each `drift_s` of slide pays into the tip, in HK$.
@export var drift_hkd: float
## The speed the sustained-speed skill starts counting at, in km/h.
@export var speed_min_kph: float
## How long the car must hold that speed before it pays, in seconds — and how
## much longer before it pays again.
@export var speed_hold_s: float
## What each `speed_hold_s` above the floor pays into the tip, in HK$.
@export var speed_hkd: float
## The share of the allowance that must be left at delivery for the early
## arrival to pay, 0..1.
@export var early_share: float
## What an early arrival pays into the tip, in HK$, over the time tip.
@export var early_hkd: float
