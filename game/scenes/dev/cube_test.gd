extends Node3D
## The cube rotates so the frame loop is visibly live — a static image cannot
## tell 60fps apart from a frozen frame.
##
## Throwaway. Delete once P0-5 has a grey-box scene worth running instead.

const SPIN_DEG_PER_S: float = 45.0

@onready var _cube: Node3D = $Cube


func _process(delta: float) -> void:
	_cube.rotate_y(deg_to_rad(SPIN_DEG_PER_S) * delta)
