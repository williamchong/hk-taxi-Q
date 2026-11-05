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
## Entries in each hourly table: a clock hour each, 0 to 23.
const HOURS: int = 24

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
## A honk is a pattern (`P3-79`): how many presses, how long each, and the gap
## between, each drawn from these ranges by why the car honks — `stood`, `cut`,
## `hit` or `close_call` (`TrafficSystem.HORN_REASONS`), x the least, y the most.
@export var horn_count: Dictionary[String, Vector2i]
@export var horn_press_s: Dictionary[String, Vector2]
@export var horn_gap_s: Dictionary[String, Vector2]
## Each honk raises the car's temper by this share; temper pushes its next draws
## toward the top of each range, never past it, and is held at `horn_temper_max`.
@export var horn_temper_step: float
@export var horn_temper_max: float
## A car's temper falls by one whole share over this many seconds.
@export var horn_temper_s: float
## The library's meshes a car is drawn from, by name, and the weight of each by
## clock hour (`Q186`): `HOURS` entries, hour 0 first, each read at a spawn in
## that hour. TD's census, by `tools/traffic_census.py`.
@export var kinds: Dictionary[String, PackedFloat32Array]
## The share of `cars` alive at each clock hour (`Q186`), `HOURS` entries: a car
## that leaves the ring is not placed again while the fleet stands at or over it.
@export var fleet_by_hour: PackedFloat32Array
## The kind among `kinds` that is a taxi (`Q183`): it wears the licence its spawn
## region's `taxi_licences` draws, and lights its roof sign when for hire.
@export var taxi_kind: String
## The share of the moving taxis whose roof sign is lit, for hire, at each spawn.
@export var taxi_for_hire: float
## A car the taxi knocks (`Q180`) coasts on its wheels for this long before its
## driver brakes, in seconds: TD's thinking time.
@export var react_s: float
## A knocked car that has come to rest waits this long before it tries to drive
## on, and as long again between tries, in seconds.
@export var recover_after_s: float
## A knocked car drives on only from within this far of a road it may drive, in
## plan metres; further off it stands.
@export var recover_radius_m: float
## ...and only facing within this many degrees of a way it may drive: it does not
## reverse, so a car turned round on a one-way street stands.
@export var recover_heading_deg: float
## How far down the road a knocked car rejoins its nearside lane, in metres.
@export var recover_ahead_m: float
## A knocked car drives on only with no other car this near where it rejoins or
## the middle of its way there, in plan metres: it looks first.
@export var recover_clear_m: float
## The fleet that keeps to a published route (`P3-78`, `Q182`), over and above
## `cars`: buses and green minibuses, each on a route that stops near it.
@export var buses: int
## How long a routed vehicle stands at its stop, in seconds.
@export var dwell_s: float
## Under this many metres short of its pole a stopped routed vehicle is at its
## stop and dwells; further back it is queued behind another.
@export var dwell_reach_m: float
## The colours a kind wears while it wanders (`Q167`: a colour that means
## something is never a livery). A minibus without a route is a red one; a kind
## not named here wears the parked roster's palette.
@export var wander_liveries: Dictionary[String, PackedColorArray]
## The colours a kind wears on a route: a minibus on one is a green one.
@export var route_liveries: Dictionary[String, PackedColorArray]
