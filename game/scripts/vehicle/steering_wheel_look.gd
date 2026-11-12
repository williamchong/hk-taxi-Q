class_name SteeringWheelLook
extends Resource
## How a car's steering wheel is drawn under the steering thumb (`Q204`, the
## user's ask: the taxi's own wheel, not a generic one). The car's, so it lives
## in its `CarSpec`; nothing in the physics reads it.
##
## Deliberately no defaults, as `CarSpec`: a missing key draws a wheel with no
## spokes, which `verify_hud` refuses.

## Each spoke's direction from the hub at straight-ahead, in degrees: 0 is
## three o'clock and 90 is six (screen y grows down).
@export var spokes_deg: PackedFloat32Array
## The hub's — the horn pad's — radius as a share of the rim's.
@export_range(0.05, 0.8, 0.01) var hub_share: float
## A spoke's width as a share of the touch stroke.
@export_range(0.2, 3.0, 0.05) var spoke_share: float
## Whether a racing wheel's stripe marks twelve o'clock. A road car has none;
## its spokes show the turn.
@export var top_stripe: bool
