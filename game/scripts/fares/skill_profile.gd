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

## How long a slide must hold at or over the drift threshold before it counts
## at all, in seconds. A shorter slide pays nothing (the user's call: a tap is
## not a drift).
@export var drift_min_s: float
## Once a slide has counted, how much longer it must hold before it pays
## again, in seconds.
@export var drift_s: float
## What a slide pays into the tip when it counts, and again each `drift_s`, in HK$.
@export var drift_hkd: float
## The speed the sustained-speed skill starts counting at, in km/h.
@export var speed_min_kph: float
## How far the car must drive at or over that speed before it pays, in metres
## — and how much further before it pays again. Distance, not time, so the
## skill can be held to the meter's own unit: `verify_fares` refuses a value
## under `FareTariff.step_m` (the user's call, `Q145`).
@export var speed_hold_m: float
## What each `speed_hold_m` at or over the floor pays into the tip, in HK$.
@export var speed_hkd: float
## How long every wheel must be off the ground before the flight counts at
## all, in seconds, judged at the landing. A kerb hop is under it.
@export var air_min_s: float
## Once a flight has counted, each further stretch of air that pays again, in
## seconds — also at the landing.
@export var air_s: float
## What a flight pays into the tip when it counts, and again each `air_s`, in
## HK$. Paid only on an upright landing.
@export var air_hkd: float
## The share of the allowance that must be left at delivery for the early
## arrival to pay, 0..1.
@export var early_share: float
## What an early arrival pays into the tip, in HK$, over the time tip.
@export var early_hkd: float
