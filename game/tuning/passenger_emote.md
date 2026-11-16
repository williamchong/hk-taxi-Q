# passenger_emote.tres

The passenger's face popping out of the back seat (`P3-49`, `Q145`; data since `Q150`). Which face
is which mesh stays on the node in `taxi.tscn`.

Every key is required: `passenger_emote_profile.gd` declares no defaults and `show_face` refuses to
pop on a zero (`PassengerEmote.usable`). `verify_vehicle.gd` asserts the scene hands the node this
resource.

- `rise_m = 1.3`: clears the roof (0.86 m) from the seat (0.55 m) with room over it.
- `life_s = 1.6`: readable from the chase camera, short enough that a paying slide does not stack
  a column of faces.
- `pop_s = 0.18`, `shrink_s = 0.3`: scale in and out, so a face pops and leaves rather than fades
  or blinks.
- `most_live = 4`: skills can pay several times a second; past this the oldest is dropped.
