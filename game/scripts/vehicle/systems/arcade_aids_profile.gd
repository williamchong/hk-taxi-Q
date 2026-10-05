class_name ArcadeAidsProfile
extends Resource
## The game's own aids (`Q155`): what no real car has, named as such, grouped
## so they are never mistaken for one of the car's systems. The rear side cut
## that starts the drift, the flick that stands drift mode in for the button,
## the cap on a caught slide's countersteer, and the player's slide lock. Read
## by `TyreVehicleController`, `FlickWatch` and `CatchLimiter`; why each value
## is what it is lives in `tuning/systems/arcade_aids.md`. No defaults
## (`Q119`): a zero is that aid off.

## Share of the rear tyres' sideways force taken away while the drift button
## is engaged, on the handling table's attack and release ramp: 0 leaves the
## handbrake alone. A locked rear still holds a city-speed turn, so the
## handbrake alone starts the slide after the corner is over (`Q153`).
@export_range(0.0, 1.0, 0.05) var drift_side_cut: float
## The cut at and above `drift_side_cut_to_kph`; `drift_side_cut` holds at and
## below `drift_side_cut_from_kph`, and the speed at the button's press picks
## between them. A slow turn asks little of the rears and needs the deeper cut;
## the same cut at 63 kph spins the car.
@export_range(0.0, 1.0, 0.05) var drift_side_cut_fast: float
@export_range(0.0, 200.0, 1.0, "suffix:kph") var drift_side_cut_from_kph: float
@export_range(0.0, 200.0, 1.0, "suffix:kph") var drift_side_cut_to_kph: float
## The flick (`P3-54`, `Q153`): seconds the steering may spend between the
## feint's side and the other before the reversal stops counting as one. 0 is
## no flick — only the drift button engages drift mode. See `FlickWatch`.
@export_range(0.0, 2.0, 0.01, "suffix:s") var flick_window_s: float
## The flick: seconds the steering must be held to the feint's side first.
@export_range(0.0, 2.0, 0.01, "suffix:s") var flick_feint_s: float
## The flick: the slowest a flick counts at.
@export_range(0.0, 200.0, 1.0, "suffix:kph") var flick_min_kph: float
## The flick: the share of an input that counts — the steering past it on a
## side, the throttle under it as lifted.
@export_range(0.05, 1.0, 0.05) var flick_input_share: float
## The lock the PLAYER has on the countersteer side while the car slides past
## the tyre's peak, where the handling table narrows it with speed. 0 leaves
## the table's lock alone. Absent from the table: swept and refuted on the
## pad's driver, kept for the user's own drive.
@export_range(0.0, 60.0, 1.0, "suffix:°") var slide_lock_deg: float
## The most the front wheels may turn on the countersteer side once a caught
## slide turns the car the other way: a cap on the player's angle, never an
## angle added. 0 leaves the player's lock alone. See `CatchLimiter`.
@export_range(0.0, 60.0, 0.5, "suffix:°") var catch_lock_deg: float
## The heading rate, the other way from the slide, past which the car reads as
## turning against it and `catch_lock_deg` caps the countersteer.
@export_range(0.0, 180.0, 1.0, "suffix:°/s") var catch_turn_dps: float
## How long after the tail was last out past the tyre's peak the cap may
## still engage, so a turn the other way after the slide is over has the full
## lock.
@export_range(0.0, 5.0, 0.05, "suffix:s") var catch_window_s: float
