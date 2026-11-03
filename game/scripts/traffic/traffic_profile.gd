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
## How far either side of a node the turn curve reaches into an edge whose
## bundle publishes no junction mouth (`trim_m`), in metres.
@export var turn_span_m: float
## How far along its edge a car takes to move from one lane to the next, in
## metres.
@export var lane_change_m: float
## How far past the mouth a car's tail runs before the indicator of the turn it
## finished goes off, in metres.
@export var wink_hold_m: float
## Under this many degrees between the way in and the way out a move is straight
## on; past it a turn, taken from the nearside lane (left) or the offside (right).
@export var straight_deg: float
## How far ahead a parked vehicle in the car's lane makes it move out a lane to
## pass, in metres (`P3-3f`).
@export var pass_look_m: float
## Room kept between a moving car's flank and a parked vehicle it passes, in
## metres: closer than this, the parked vehicle is in its lane.
@export var side_clear_m: float
## How far short of its line a car looks for one whose turn crosses its own,
## and how near its own line a car coming must be to be given way to, in metres.
@export var give_way_look_m: float
## Voices of the horn at once (`Q178`).
@export var horn_voices: int
## Where a horn fades to nothing, in metres: a voice's `max_distance`.
@export var horn_range_m: float
## A car does not sound its horn again for this long, in seconds.
@export var horn_repeat_s: float
## How long a car stands behind the taxi, with no red to wait for, before it
## sounds its horn, in seconds.
@export var horn_after_s: float
## A car sounds its horn at once when the taxi leaves it this far over the speed
## it could still stop from, in m/s: it has been cut up.
@export var horn_cut_mps: float
## Each car's horn is pitched up to this fraction either side of the file's.
@export var horn_pitch_spread: float
## The library's meshes a car is drawn from, by name, and the weight of each.
@export var kinds: Dictionary[String, float]
