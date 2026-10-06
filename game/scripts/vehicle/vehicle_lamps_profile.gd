class_name VehicleLampsProfile
extends Resource
## The taxi's lamp dials (`P3-11d`) — the indicators, the roof sign, the light
## probe and the thrown beams — the numbers `vehicle_lamps.gd` carried as
## `@export` defaults until `Q150` moved them, against `ARCHITECTURE.md`'s
## Constraint 4: tuning is data. The rationale for each value is in
## `tuning/vehicle_lamps.md`; what each *is* is here. How bright a lamp is and
## how far it reaches stay in `taxi.tscn`, on the lamp: those are the fitting's,
## not the state's.
##
## 🔴 **No `@export` here declares a default**, on `WrongWayProfile`'s
## convention: a default is a second copy of the tuning table, and a second copy
## drifts — Godot's writer also drops any key equal to one, which is how
## `beams.tres` went empty (`Q119`). A missing key reads as zero, and
## `VehicleLamps` refuses to run on a zero where a zero would divide or never
## flash, rather than fall back to a literal. Nine keys here may legally be
## zero (their export floor), so a missing one of those cannot be told from a
## chosen one; `tuning/vehicle_lamps.md` names them.

## Path to the shipped table, so `taxi.tscn` and `verify_vehicle.gd` cannot load
## two different files.
const PATH: String = "res://tuning/vehicle_lamps.tres"

@export_group("Indicators")
## Flashes per second.
@export_range(0.5, 4.0, 0.05) var blink_hz: float
## Share of each flash the lamp is lit for.
@export_range(0.1, 0.9, 0.05) var blink_duty: float
## How much lock counts as a turn, as a fraction of the lock available at this
## speed. See `VehicleController.steer_ratio` — a fraction rather than an angle,
## because full lock at 140 km/h is a quarter of full lock parked.
@export_range(0.0, 1.0, 0.01) var steer_threshold: float
## How long lock has to be *held* one way before the indicator comes on.
@export_range(0.0, 3.0, 0.05) var steer_hold_s: float

@export_group("Roof sign")
## How hard the illuminated box on the roof burns, when `for_hire` lights it.
@export_range(0.0, 1.0, 0.05) var sign_lit: float

@export_group("Tail lamps")
## How hard the brake lenses burn as tail lamps while the front lamps are on,
## against the brake's own 1.0.
@export_range(0.0, 1.0, 0.05) var tail_lit: float

@export_group("Light probe")
## How far the shadow probe looks along the sun before calling the car sunlit.
@export_range(10.0, 400.0, 5.0, "suffix:m") var sun_probe_m: float
## How far straight up the cover probe looks before calling the sky open.
@export_range(2.0, 100.0, 1.0, "suffix:m") var cover_probe_m: float
## Where both probes start, above the car's origin.
@export_range(0.0, 4.0, 0.05, "suffix:m") var probe_height_m: float
## How often the two probes are cast, against a 60 Hz physics tick.
@export_range(1.0, 60.0, 1.0, "suffix:Hz") var probe_hz: float
## How long a *darker* reading must persist before the lamps follow it.
@export_range(0.0, 5.0, 0.05, "suffix:s") var dark_hold_s: float
## How long a *lighter* reading must persist before the lamps go out.
@export_range(0.0, 10.0, 0.05, "suffix:s") var light_hold_s: float

@export_group("Thrown beams")
## What share of the beam the side lamps throw, in energy and in reach.
@export_range(0.0, 1.0, 0.01) var sidelamp_beam: float
## Key-light energy at or below which the rig counts as night.
@export_range(0.0, 1.0, 0.01) var night_energy: float
