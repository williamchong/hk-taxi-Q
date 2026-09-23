class_name FareProfile
extends Resource
## The fare loop's radii, dwells, bars and rates (`P3-1a`, `Q141`): what each
## number *is*. Why each has the value it has is `tuning/fares.md` beside the
## `.tres`. The money the meter runs on is `FareTariff`, a separate table,
## because one is Transport Department's and the other is ours.
##
## 🔴 **No `@export` here declares a default**, on `WrongWayProfile`'s
## convention: a default is a second copy of the tuning table, and a second copy
## drifts. A missing key reads as zero, and `FareSystem` refuses to run on a
## zero radius, bar or rate rather than fall back to a literal.

## Path to the shipped table, so `fare_system.gd` and `verify_fares.gd` cannot
## load two different files.
const PATH: String = "res://tuning/fares.tres"

## How close to a pickup's stop point the car must be to hail, in metres of
## plan distance.
@export var hail_radius_m: float
## How long the car must stay inside that radius after the hail before the
## passenger is aboard, in seconds. Leaving during it cancels the hail.
@export var board_s: float
## How close to the destination's stop point the car must be to deliver, in
## metres of plan distance.
@export var deliver_radius_m: float
## Below this the car counts as stopped, for both the hail and the delivery,
## in km/h.
@export var stop_below_kph: float
## The shortest legal route a destination may be drawn at, in metres.
@export var min_trip_m: float
## The speed the allowance is priced at over the legal route, in km/h.
@export var par_kph: float
## The least allowance a short hop (a `pudo` destination) gets, in seconds.
@export var short_hop_floor_s: float
## The least allowance a standard fare (a `taxi_stand` destination) gets, in
## seconds.
@export var standard_floor_s: float
## What each second left on the allowance at delivery pays as a tip, in HK$.
@export var tip_hkd_per_s: float
## How often the loop samples the car against the graph, in hertz.
@export var sample_hz: float
