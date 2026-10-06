class_name PropCellProfile
extends Resource
## Which prop layers `layer_preview.gd` stands as a `MultiMesh` per plan cell
## rather than one per region, and how far away a cell is still drawn
## (`P3-67`, `Q135`). The rationale for each value is in `tuning/prop_cells.md`;
## what each *is* is here.
##
## 🔴 **No `@export` here declares a default**, on `StreamingProfile`'s
## convention: a missing key reads as zero, and the preview refuses a zero cell
## rather than fall back to a literal.

## Path to the shipped table, so `layer_preview.gd` and `verify_city.gd` cannot
## load two different files.
const PATH: String = "res://tuning/prop_cells.tres"

## Ids of `GeneratedLayer.LAYERS` whose placements are cut into cells. A layer
## not named here stays one `MultiMesh` a library mesh.
@export var layers: PackedStringArray
## Side of a plan cell. A placement goes whole to the cell its origin is in.
@export_range(0.0, 2000.0, 5.0, "suffix:m") var cell_m: float
## A cell is hidden past this, measured from the camera to the CENTRE of the
## cell's own box — the engine's `visibility_range_end`.
@export_range(0.0, 2000.0, 5.0, "suffix:m") var range_m: float
## The engine's `visibility_range_end_margin`: the hysteresis about `range_m`.
@export_range(0.0, 100.0, 1.0, "suffix:m") var range_margin_m: float
