# anti_lock_brakes.tres

Rationale for `game/tuning/systems/anti_lock_brakes.tres`. Each heading is the line the block sat above; `Overview` is
the file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

A real car's ABS (`Q155`): the foot brake on a wheel starting to lock is released for the substep,
so the tyre stays near its peak and the fronts still steer. Never the handbrake. Built with
`HandlingProfile.brake_front_share` on the user's ask for faster braking (2026-10-06): with the
brake equal on all four wheels the rears locked under the load moving forward while the fronts
had grip to spare, so the stop was 0.8 g and a stronger brake barely moved it.

## `slip_limit = 1.0`

Swept 0 / 0.8 / 1.0 / 1.5 / 2.0 at `brake_force` 47: no change (7.8 m/s²) — the wheels were not
locking; the brake itself was the limit (47 × 60 ticks × 0.31 m ≈ 870 N⋅m a wheel, ≈ 8.1 m/s² on
1,400 kg). With the brake raised to 70 and 65% of it on the front (`HandlingProfile`), ABS holds
the stop at the tyre's limit: 9.0 / 9.3 / 9.4 m/s² from 42 / 63 / 86 kph, 15.9 m from 63 (19.5 at
47); past 70 nothing moves. A real car with ABS on a road tyre stops at about 0.95 g.
