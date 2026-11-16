# anti_lock_brakes.tres

A real car's ABS (`Q155`): the foot brake on a wheel starting to lock is released for the substep,
so the tyre stays near its peak and the fronts still steer. Never the handbrake.

- `slip_limit = 1.0`: the tyre's peak. With `CarSpec.brake_front_share` 0.65 it holds the stop at
  the tyre's limit: 9.0–9.4 m/s² from 42–86 kph, 15.9 m from 63 kph. With the brake equal on all
  four wheels the rears locked first and the stop was 0.8 g.
