class_name StreetTrackerProfile
extends Resource
## The street plate's dwell (`P5-26`) — `street_tracker.gd`'s one constant
## until `Q124`'s re-read, against `ARCHITECTURE.md`'s Constraint 4. Rationale
## in `tuning/street_tracker.md`.
##
## 🔴 **No `@export` here declares a default**, on `HudStyle`'s convention;
## `StreetTracker` refuses a zero dwell rather than fall back to a literal.

## Path to the shipped table, so `hud.gd` and `verify_hud.gd` cannot load two
## different files.
const PATH: String = "res://tuning/street_tracker.tres"

## How long a different street must stay nearest before the plate follows it,
## in seconds — seconds and not metres, because the artefact suppressed is a
## name changing faster than it can be read.
@export var dwell_s: float
