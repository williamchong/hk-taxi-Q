class_name FareTariff
extends Resource
## The urban taxi tariff the 咪錶 runs (`P3-1a`, `Q141`): what each number
## *is*. The values and their source — Transport Department's published fare
## table, effective 14 July 2024 — are `tuning/tariff.md` beside the `.tres`.
##
## 🔴 **No `@export` here declares a default**, on `WrongWayProfile`'s
## convention: a default is a second copy of the tuning table, and a second copy
## drifts. A missing key reads as zero, and `FareMeter` refuses to construct on a
## zero flagfall or step rather than fall back to a literal.
##
## ⚠️ Money is a `float` here because that is what a `.tres` carries legibly;
## `FareMeter` converts every amount to integer cents at construction and does
## its arithmetic there, so 29 + 35 × 2.1 lands on 102.50 and not beside it.

## Path to the shipped table, so `fare_system.gd` and `verify_fares.gd` cannot
## load two different files.
const PATH: String = "res://tuning/tariff.tres"

## What the meter shows the moment the passenger boards, in HK$.
@export var flagfall_hkd: float
## How far the flagfall carries, in metres. TD: "first 2 kilometres or any part
## thereof".
@export var flagfall_m: float
## The distance unit after the flagfall, in metres.
@export var step_m: float
## The waiting-time unit after the flagfall, in seconds. One unit is a `step_m`
## driven **or** a `step_s` elapsed, whichever comes first.
@export var step_s: float
## What a unit costs while the reading is below `threshold_hkd`, in HK$.
@export var step_hkd: float
## What a unit costs once the reading has reached `threshold_hkd`, in HK$.
@export var step_hkd_after: float
## The reading at which the unit price drops to `step_hkd_after`, in HK$.
@export var threshold_hkd: float
