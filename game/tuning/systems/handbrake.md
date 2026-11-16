# handbrake.tres

The handbrake (Space): a torque on each rear wheel, as a real car's.

- `lock_ratio = 1.0815` (`Q156`): the torque in multiples of what just locks a rear wheel at rest
  (`mu` on the wheel's share of the weight, at its radius;
  `TyreVehicleController._handbrake_torque_nm`). A ratio, so it follows mass, gravity and grip; as
  hand-sized newtons it was re-seeded at every such change. On the taxi it is 1,150 N·m of a
  1,063 N·m lock. Not lower: about 0.94 (1,000 N·m) brings the countersteered `turn` at 86 kph out
  at 54° and the tap under a slide at 63 / 86. Not higher: about 1.2 (1,275 N·m) puts the tap at
  86 kph to 87.6° against 37.3°.
