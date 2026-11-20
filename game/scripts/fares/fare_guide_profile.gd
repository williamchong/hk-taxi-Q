class_name FareGuideProfile
extends Resource
## The world-space guide to the fare (`P3-5a`, `Q142`): the arrow over the
## taxi and the ring on the road at the target, and how both answer distance.
##
## Every field is required (`Q119`): `tuning/guide.tres`, rationale in
## `guide.md` beside it. No defaults here, for `HudStyle`'s reason.

const PATH: String = "res://tuning/guide.tres"

## Beyond `far_m` the guide is at its far look; inside `near_m` at its near.
@export var near_m: float
@export var far_m: float
## The arrow's length at each end, in metres, and its height over the car.
@export var arrow_near_m: float
@export var arrow_far_m: float
@export var height_m: float
## The colours at each end: red far, green near (the user's call); and the
## pending customers' rings, the map's amber restated here so this profile
## owns every colour the guide draws.
@export var far_colour: Color
@export var near_colour: Color
@export var pending_colour: Color
## The ring on the road at the target: its radius and band, how far above
## the surface it floats, and the pulse.
@export var ring_radius_m: float
@export var ring_width_m: float
@export var ring_lift_m: float
@export var pulse_hz: float
@export var pulse_depth: float
@export var ring_alpha: float
## The solid pointer hung over every ring so a target reads from afar: the
## gap from the ring up to its tip, its length and width, and its bob and spin.
@export var pointer_height_m: float
@export var pointer_length_m: float
@export var pointer_width_m: float
@export var pointer_bob_m: float
@export var pointer_bob_hz: float
@export var pointer_spin_hz: float
