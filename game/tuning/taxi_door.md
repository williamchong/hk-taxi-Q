# taxi_door.tres

The passenger door's swing (`P3-48`; data since `Q150`). Which door, which way and its material are
`taxi.tscn`'s and `make_vehicle.py`'s.

Every key is required (`taxi_door_profile.gd` declares no defaults). The door refuses to swing on a
zero `open_deg` or `swing_s` (`TaxiDoor.usable`). `alight_hold_s` may legally be 0, so a missing
one is not guarded: the door shuts the moment it opens. `verify_vehicle.gd` asserts the scene hands
the node this resource.

- `open_deg = 65.0`: at 90° the leaf is edge-on to the chase camera and vanishes; 65° keeps its
  face towards a camera behind the car.
- `swing_s = 0.35`: under `fares.tres`'s `board_s`, so the door stands open for most of a boarding.
- `alight_hold_s = 0.8`: how long `open_briefly` holds the door open before shutting. The hold
  starts once the door is fully open.
