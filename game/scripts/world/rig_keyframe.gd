## One authored time of day on a `RigCycle` (`Q160`): everything a `LightingRig`
## blends toward as game time passes.
##
## The DAY is not one of these. The rig scene as authored — its `Environment`,
## its `Sun` — is the day, read off the scene at `_ready`, so the daylight
## numbers keep exactly one home and a cycle pinned at 0 is the scene untouched.
##
## 🔴 **No `@export` here declares a default** (`Q150`'s convention): a default
## is a second copy of the tuning table and Godot's writer drops any key equal
## to one. The rationale for each value is in `tuning/day_to_night.md`.
class_name RigKeyframe
extends Resource

## Where on the cycle this look is reached, as a fraction of `RigCycle.length_s`.
@export_range(0.0, 1.0, 0.01) var at: float
## The sky, ambient, fog and glow at this time. Only the properties
## `LightingRig.BLENDED` and `LightingRig.BLENDED_SKY` name are read; the
## switches (`glow_enabled`, `tonemap_mode`, …) stay the day's.
@export var environment: Environment
## The key light's `rotation_degrees` at this time.
##
## ⚠️ **Never below the horizon with energy left in it**, and never a deleted
## light: `VehicleLamps.read_rig` reads a missing sun as "no rig" and drives
## dark. Night is a dim key light, the moon's, not an absent one.
@export var sun_rotation_deg: Vector3
@export var sun_colour: Color
@export_range(0.0, 4.0, 0.01) var sun_energy: float
## The `sky_light` shader global: what the façades' glazing and the car's
## paint multiply their painted sky reflection by. White is the day.
@export var sky_light: Color
## The `night_lights` shader global, 0 by day and 1 at full night: the one
## dial every lit layer — the lanterns and their pools, the floodlights, the
## road paint, the outline — multiplies its own `.tres` strength by.
@export_range(0.0, 1.0, 0.01) var night_lights: float
