# guide.tres

Rationale for `game/tuning/guide.tres` (`Q119`).

The world-space guide to the fare (`P3-5a`, `Q142`): an arrow over the taxi that grows and turns
green as the target nears, and a ring on the road where the customer waits or the passenger gets
out. Both read plan metres from the car to the stop point.

Every key is required: `fare_guide_profile.gd` declares no defaults, and `verify_hud.gd` refuses a
zero it would draw with.

- `near_m` 30, `far_m` 400: inside `near_m` the guide is at its near look, beyond `far_m` at its
  far. Most of a trip reads "far"; the change is the last few blocks. A first guess.
- `arrow_near_m` 2.4, `arrow_far_m` 1.0, `height_m` 2.6: the arrow's length near and far, and its
  height over the car. It grows as it starts to matter.
- `far_colour` red, `near_colour` green: the guide's own colours, not the map's.
- `pending_colour`: every pending customer's ring while no one is aboard, one multimesh. The same
  amber as `hud_style.tres`'s `map_pickup`, restated here on purpose. The destination's ring
  alone takes the distance colour.
- `ring_radius_m` 4.0, `ring_width_m` 0.6, `ring_lift_m` 0.08: a car length across, floated above
  the road's own paint.
- `pulse_hz`, `pulse_depth`, `ring_alpha`: the ring pulses by `pulse_depth` of its size,
  alpha-blended.
