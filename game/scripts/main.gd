extends Node
## The entry point (`P5-24`): the one node that holds both `World` and `GUI`,
## and therefore the one that may hand the HUD its car.
##
## The guide's rule is that siblings know only their own hierarchies and an
## ancestor mediates; before this the HUD found the first car in a group,
## which crossed the World / GUI boundary from below. A level change swaps
## `World`'s child and hands the next car in here — nothing under `GUI`
## searches for one.

## The level in play. Assign in the scene.
@export var level: DriveHarness
## The player's HUD. Assign in the scene.
@export var hud: Hud


func _ready() -> void:
	# After `World` and `GUI` have readied: children ready first, so the level
	# has placed its car and the HUD has built its plate before this runs.
	if hud == null:
		push_warning("Main has no HUD assigned; the plate and the speed will not draw.")
		return
	if level == null:
		push_warning("Main has no level assigned; the HUD has no car to read.")
		return
	hud.vehicle = level.vehicle
