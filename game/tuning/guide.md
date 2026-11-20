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
- `pointer_*` (`Q261`, the user's ask): a solid four-sided spike over every ring — the destination's
  in the distance colour, each pending customer's in `pending_colour` — because a flat ring on
  the road is lost a block or two out. Opaque and unshaded, its faces shaded by baked vertex
  colours, so it reads the same at night. All first guesses, for the user's pick from frames:
  - `pointer_height_m` 3.0: the gap from the ring to the tip, over a car roof, under a bus's.
  - `pointer_length_m` 2.0, `pointer_width_m` 1.4: the spike, tip to cap and corner to corner.
  - `pointer_bob_m` 0.4 at `pointer_bob_hz` 0.6: the tip rises from `pointer_height_m` by up to
    this, never sinks below it.
  - `pointer_spin_hz` 0.25: one turn in four seconds, so the shaded faces catch the eye.
