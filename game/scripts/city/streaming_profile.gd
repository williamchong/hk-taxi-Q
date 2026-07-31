class_name StreamingProfile
extends Resource
## What `CityStreamer` loads, at which tier, and when it lets go (`P2-1`).
##
## CLAUDE.md hard rule 4: tuning values are data, never constants in code. This
## script declares the schema and nothing else — the numbers live only in
## game/tuning/streaming.tres. Deliberately no defaults, like HandlingProfile:
## an unassigned profile reads as all-zeroes and unloads the whole city in front
## of you, which is a loud failure rather than a quiet one running on constants
## buried in a script.

@export_group("Distance bands")
## Outer edge of each LOD tier, in metres, nearest tier first.
##
## Tier `k` covers `(tier_distances_m[k - 1], tier_distances_m[k]]`, and anything
## past the last edge takes the coarsest tier the tile actually has. So two
## entries describe three tiers, which is what `lod_cell_sizes_m` produces for
## Hong Kong today — the array is not fixed at two because tier count is city
## config, and a city built with four tiers must be describable here.
##
## ⚠️ Measured to the tile's **AABB**, never to its grid square. Buildings are
## assigned to a tile whole and overhang it — Wan Chai's tiles span a median
## 165 m on a 150 m grid, up to 222 m — so grid-square distance would switch a
## tile's tier while half its geometry was still under the camera.
@export var tier_distances_m: PackedFloat32Array

## Past this the tile is freed altogether.
##
## Pair it with the camera's far plane rather than tuning it alone: `P1-7`
## measured Wan Chai's chase camera at 400 m, past which a street canyon shows
## nothing anyway. Unloading nearer than the far plane is visible as buildings
## vanishing at the horizon; unloading further just holds memory nothing draws.
@export_range(0.0, 2000.0, 5.0, "suffix:m") var unload_distance_m: float

## Distance a tile must travel *past* a band edge before its tier changes.
##
## Without it a tile sitting exactly on an edge reloads every frame the camera
## jitters — the classic streaming thrash, and it costs a disk read each time.
## The band a tile is already in is widened by this on both sides, so the
## hysteresis is symmetric and a tile crossing outward re-enters at the same
## place it left.
@export_range(0.0, 100.0, 1.0, "suffix:m") var hysteresis_m: float

@export_group("Load budget")
## Threaded loads allowed in flight at once.
##
## The load itself is off the main thread, so this bounds I/O and memory churn
## rather than frame time — `max_instantiations_per_frame` is the one that
## bounds the hitch.
@export_range(1, 32, 1) var max_loads_in_flight: int

## Tiles turned into scene nodes per frame.
##
## This is the hitching control. `ResourceLoader` does the disk read and the
## mesh parse on a worker thread, but `PackedScene.instantiate` and adding to
## the tree are main-thread work, so a camera entering a dense block would
## otherwise instantiate a dozen tiles in one frame and drop it.
@export_range(1, 16, 1) var max_instantiations_per_frame: int
