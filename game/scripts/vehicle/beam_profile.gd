## How many thrown beams the renderer can actually pay for.
##
## A tuning resource rather than a constant, because it is a **hardware fact with
## a number in it** and hard rule 4 puts those in `.tres`. The number is not a
## taste: Forward Mobile pairs a fixed list of spot lights per rendered object
## and the fragment shader loops that list, so the ninth light on an object is
## not dimmer — it is **absent**, with no warning and no fallback.
##
## ⚠️ **The competition is per *object*, and `roads.glb` is one mesh for the whole
## region.** Every beam in the game therefore contends for the same list whenever
## the road is on screen, which is always. Two lamps a car makes `max_spot_lights`
## a **car** count once divided, and that is why this cannot be left to
## `distance_fade` — fade bounds who competes, it does not cap how many win.
class_name BeamProfile
extends Resource

## Spot lights the renderer will honour on one object at once.
##
## 8 is measured, not quoted: brightness was linear to eight and **exactly zero**
## from the ninth. Lower it to buy headroom for anything else that throws a spot;
## raising it past the driver's own limit buys nothing and hides the cliff again.
@export_range(0, 16, 1) var max_spot_lights: int = 8

## How often the grant is re-ranked, in hertz.
##
## ⚠️ **Deliberately not every frame.** The ranking is a sort over every car with
## a lamp rig, and beams that re-rank at frame rate *swap* at frame rate — a car
## a metre either side of the cut flickers as the order churns. Slow enough that
## a swap reads as a car arriving, fast enough that it has arrived before the
## player is past it.
@export_range(1.0, 60.0, 1.0) var regrant_hz: float = 6.0

## Extra distance a rig must make up before it takes a lit rig's slot, in metres.
##
## Hysteresis, and the reason two cars driving abreast do not trade beams every
## regrant. Costs nothing when the field is not tied, which is most of the time.
@export_range(0.0, 50.0, 0.5) var swap_margin_m: float = 8.0
