class_name FarViewProfile
extends Resource
## How far a region's far version is drawn from (`Q249`): `city_layer.gd` hides
## one whose box is further from the camera than `max_far_m`.
##
## CLAUDE.md hard rule 4: the numbers live only in game/tuning/far_view.tres,
## and their reasons in far_view.md beside it. No defaults, like
## `StreamingProfile`: an unassigned profile reads as 0 m and hides every far
## version, which is a loud failure rather than a quiet one.

## Past this the far version is hidden, in metres from the camera to the
## nearest point of the mesh's box. The fog has nearly erased a block by then,
## so the cut does not show.
@export_range(0.0, 50000.0, 10.0, "suffix:m") var max_far_m: float

## Distance a box must travel past `max_far_m` before it is shown or hidden
## again, so one on the edge does not flicker as the camera shakes.
@export_range(0.0, 2000.0, 10.0, "suffix:m") var hysteresis_m: float
