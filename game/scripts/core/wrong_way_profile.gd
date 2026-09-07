class_name WrongWayProfile
extends Resource
## The wrong-way sign's bars and dwells (`P5-26`) — the numbers
## `wrong_way_monitor.gd` carried as constants until `Q124`'s re-read found
## them, against `ARCHITECTURE.md`'s Constraint 4: tuning is data. The
## rationale for each value is in `tuning/wrong_way.md`; what each *is* is here.
##
## 🔴 **No `@export` here declares a default**, on `HudStyle`'s convention: a
## default is a second copy of the tuning table, and a second copy drifts. A
## missing key reads as zero, and `WrongWayMonitor` refuses to construct on a
## zero dwell or bar rather than fall back to a literal.

## Path to the shipped table, so `hud.gd` and `verify_hud.gd` cannot load two
## different files.
const PATH: String = "res://tuning/wrong_way.tres"

## How long the car must be going the wrong way before the sign goes up, in
## seconds — seconds and not metres, because the artefact suppressed is a sign
## appearing at a junction the player is driving straight through.
@export var raise_s: float
## How long the car must be going the right way before it comes down. Longer
## than the raise: that asymmetry is the hysteresis.
@export var clear_s: float
## How far off the legal direction the car must be **pointed** to count as
## against it, in degrees. The nose only.
@export var angle_deg: float
## Below this the car is not going anywhere and its velocity is noise. Read on
## the withholding side only.
@export var min_kph: float
## How close to the legal direction the car must be *travelling* before its
## wheels may withhold the sign, in degrees. 🔴 A second bar, never the one
## above — reusing it was a defect (`Q81`).
@export var correcting_angle_deg: float
