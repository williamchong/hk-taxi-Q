## How many thrown beams the renderer can actually pay for.
##
## A tuning resource rather than a constant, because it is a **hardware fact with
## a number in it** and hard rule 4 puts those in `.tres`. The number is not a
## taste: Forward Mobile pairs a fixed list of spot lights per rendered object
## and the fragment shader loops that list, so the ninth light on an object is
## not dimmer — it is **absent**, with no warning and no fallback.
##
## ⚠️ **The competition is per *object*, and the road under the car is one
## object** — the whole region until `P5-6`, one 150 m chunk since. Every beam on
## the same chunk therefore contends for the same list, and the budget stays as
## that bound. Two lamps a car makes `max_spot_lights`
## a **car** count once divided, and that is why this cannot be left to
## `distance_fade` — fade bounds who competes, it does not cap how many win.
##
## 🔴 **No `@export` here declares a default**, on `WrongWayProfile`'s
## convention (`Q150`): a default is a second copy of the tuning table, and a
## second copy drifts — and Godot's writer drops any key equal to one, which is
## how `tuning/beams.tres` shipped EMPTY for a while, every value living only
## here. A missing key reads as zero, and `BeamBudget` refuses the table rather
## than fall back to a literal. The rationale for each value is in
## `tuning/beams.md`; what each *is* is here.
class_name BeamProfile
extends Resource

## Path to the shipped table. `beam_budget.gd` restates it as a literal — it may
## not name this class — and `verify_beam_budget.gd` pins the two equal.
const PATH: String = "res://tuning/beams.tres"

## Spot lights the renderer will honour on one object at once.
@export_range(0, 16, 1) var max_spot_lights: int
## How often the grant is re-ranked, in hertz.
@export_range(1.0, 60.0, 1.0) var regrant_hz: float
## Extra distance a rig must make up before it takes a lit rig's slot, in metres.
@export_range(0.0, 50.0, 0.5) var swap_margin_m: float
