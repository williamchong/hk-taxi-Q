class_name TramProfile
extends Resource
## How the trams run (`P3-4`, `Q176`). The rationale for each value is in
## `tuning/trams.md`; what each *is* is here.
##
## 🔴 **No `@export` here declares a default**, on `HudStyle`'s convention: a
## missing key reads as zero, and `TramSystem` refuses to run on a zero rather than
## fall back to a literal.

## Path to the shipped table, so the system and `verify_trams.gd` cannot load two
## different files.
const PATH: String = "res://tuning/trams.tres"

## Trams on the lines at once.
@export var trams: int
## Running speed, in m/s.
@export var cruise_mps: float
## Acceleration, in m/s².
@export var accel_mps2: float
## The braking a tram plans a stop at, in m/s².
@export var brake_mps2: float
## The hardest a tram may brake on a tick, in m/s²: what one cut up uses.
@export var brake_max_mps2: float
## Seconds with the doors open at a stop.
@export var dwell_s: float
## Bumper to bumper behind whatever is ahead, in metres.
@export var gap_m: float
## How far down the rails a tram looks, nose to what is there, in metres.
@export var look_m: float
## Another tram or a car is followed within this many degrees of the same heading.
@export var follow_heading_deg: float
## A tram sets out only with this much clear of its start, in plan metres.
@export var start_clear_m: float
## A route runs on this far past each end of its line, in metres.
@export var run_off_m: float
## How far either side of the middle each bogie stands, in metres.
@export var bogie_m: float
## The taxi's half-length, as far as stopping short of it goes, in metres.
@export var taxi_half_m: float
## How far apart a line's end and the next region's may stand and join, in metres.
@export var seam_join_m: float
## ...and the most their headings may differ, in degrees.
@export var seam_heading_deg: float
## Voices of the bell at once.
@export var bell_voices: int
## A tram further from the listener than this does not ring, in plan metres.
@export var bell_range_m: float
## Seconds between rings at something standing in the way.
@export var bell_repeat_s: float
