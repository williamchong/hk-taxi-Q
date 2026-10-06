class_name CarOutlineProfile
extends Resource
## The outline's answer to the car (`P3-65`): how fast is "full speed" for the
## city's line. The value and its reason are `tuning/car_outline.md`'s; the
## drift's light tail is `LightTailProfile`'s.

const PATH: String = "res://tuning/car_outline.tres"

## The speed at which `outline_speed` reaches 1 and the city's line is at its
## thinnest and faintest; it holds there above.
@export_range(10.0, 300.0, 1.0, "suffix:kph") var full_speed_kph: float
