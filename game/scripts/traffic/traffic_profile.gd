class_name TrafficProfile
extends Resource
## How the traffic drives and where it lives (`P3-3c`, `Q173`). The rationale
## for each value is in `tuning/traffic.md`; what each *is* is here.
##
## 🔴 **No `@export` here declares a default**, on `HudStyle`'s convention: a
## missing key reads as zero, and `TrafficSystem` refuses to run on a zero
## rather than fall back to a literal.

## Path to the shipped table, so the system and `verify_traffic.gd` cannot load
## two different files.
const PATH: String = "res://tuning/traffic.tres"

## Cars alive at once round the player.
@export var cars: int
## A car is placed no nearer the player than this, in plan metres.
@export var spawn_min_m: float
## ...and no further than this.
@export var spawn_max_m: float
## A car further than this from the player is taken away, in plan metres.
@export var retire_m: float
## No car is placed nearer another than this, in plan metres.
@export var spawn_clear_m: float
## A car cruises at this fraction of its edge's speed limit.
@export var cruise_of_limit: float
## Speed through a junction's turn curve, at most, in m/s.
@export var turn_mps: float
## Acceleration, in m/s².
@export var accel_mps2: float
## The braking a car plans a stop at — the light and the car ahead — in m/s².
@export var brake_mps2: float
## The hardest a car may brake on a tick, in m/s²: what a car cut up uses.
@export var brake_max_mps2: float
## Bumper to bumper behind a car stopped ahead, in metres.
@export var gap_m: float
## How far ahead a car looks for a car to follow, in plan metres.
@export var look_m: float
## A car ahead is followed only within this many degrees of the same heading;
## past it the two are crossing, not queueing.
@export var follow_heading_deg: float
## How far either side of a node the turn curve reaches into each edge, at most,
## in metres.
@export var turn_span_m: float
## The library's meshes a car is drawn from, by name, and the weight of each.
@export var kinds: Dictionary[String, float]
