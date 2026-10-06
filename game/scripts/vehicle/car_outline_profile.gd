class_name CarOutlineProfile
extends Resource
## The outline's answers to the car (`P3-65`): how fast is "full speed" for the
## city's line, and the car's afterimage while it drifts. The values and their
## reasons are `tuning/car_outline.md`'s.

const PATH: String = "res://tuning/car_outline.tres"

## The speed at which `outline_speed` reaches 1 and the city's line is at its
## thinnest and faintest; it holds there above.
@export_range(10.0, 300.0, 1.0, "suffix:kph") var full_speed_kph: float
## The afterimage's width at the moving end — the end of the car moving most,
## dragged; none short of `drag_from` (the user, 2026-10-07).
@export_range(0.005, 0.2, 0.005, "suffix:m") var hull_width_m: float
## Where along the half-length toward that end the afterimage starts: 0 the
## middle, 1 the very end.
@export_range(0.0, 0.95, 0.05) var drag_from: float
## The afterimage's strength at its tip, so it reads as a ghost of the car.
@export_range(0.05, 1.0, 0.05) var ghost: float
## How the afterimage seeps in when a slide starts counting and drains when it stops:
## the time constant of each ease. Never a snap.
@export_range(0.01, 2.0, 0.01, "suffix:s") var seep_s: float
@export_range(0.01, 3.0, 0.01, "suffix:s") var drain_s: float
## The tail: the car's sideways speed times this is how far it trails behind,
## capped at `smear_max_m` — short, so it never pulls the eye off the road.
@export_range(0.01, 1.0, 0.01, "suffix:s") var smear_s: float
@export_range(0.05, 3.0, 0.05, "suffix:m") var smear_max_m: float
## The car's paint, which the afterimage is drawn in, darkened: one colour, the
## car's outermost edge, never a copy of its lamps and glass (the user,
## 2026-10-07). The taxi's red, `make_vehicle.py`'s body colour.
@export var rim_colour: Color
## The city's line, for its `surface_darkness`: the afterimage is drawn in the car's
## own outline colour by reading the one number that makes it.
@export var city_line: ShaderMaterial
