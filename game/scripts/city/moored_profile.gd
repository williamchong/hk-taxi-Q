class_name MooredProfile
extends Resource
## How a moored hull rocks at its berth (`Q254`): `moored.gd` turns these into
## a heave, a roll and a pitch, each one sine.
##
## CLAUDE.md hard rule 4: the numbers live only in game/tuning/moored.tres,
## and their reasons in moored.md beside it. No defaults, like
## `FarViewProfile`: an unassigned profile reads as zero and the hull stands
## still, which `verify_landmarks.gd` refuses.

## How far the hull rises and falls about its rest at the water level.
@export_range(0.0, 1.0, 0.01, "suffix:m") var heave_m: float

## One rise and fall.
@export_range(0.5, 30.0, 0.1, "suffix:s") var heave_period_s: float

## How far the hull leans side to side, about its long axis.
@export_range(0.0, 10.0, 0.05, "suffix:°") var roll_deg: float

## One lean to each side and back.
@export_range(0.5, 30.0, 0.1, "suffix:s") var roll_period_s: float

## How far the ends dip and lift, about the beam.
@export_range(0.0, 10.0, 0.05, "suffix:°") var pitch_deg: float

## One dip of each end and back.
@export_range(0.5, 30.0, 0.1, "suffix:s") var pitch_period_s: float
