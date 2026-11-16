# pace.tres

The game's pace as one scale for every car (`Q156`). The world is scaled, never the car: gravity is
multiplied by `pace_scale` and every force the car makes follows it (`PaceProfile` lists what takes
the scale, its root, or nothing). That is the real car on a road where everything happens
`√pace_scale` times as fast, at the same slip angles and the same share of each tyre's grip. It
buys the arcade envelope without touching the tyre's `mu` 1.0 (`tyre.md`).

The player is not scaled. Input dials in seconds stay in seconds (`steer_attack_s`, the flick's
windows, the pad's driver). The systems' own clocks (`drift_mode.rearm_s`, the catch limiter's
window and rate, the drift button's ramp) run at the pace. A slide at pace 2 is the pace-1 slide in
0.71 of the seconds with the same hands.

## `pace_scale = 2.0`

The user's pick from a street drive, and the 60 Hz tick's ceiling. The scaling is exact while the
tick resolves the wheels and springs; past 2.0 it does not, and a faster pace needs a faster
physics tick first, not this dial:

| pace at 60 Hz | 1.0 | 1.5 | 2.0 | 2.5 | 4.0 |
|---|---|---|---|---|---|
| brake from 42 kph × √pace, m/s² ÷ pace | 9.12 | 9.16 | 9.06 | 7.86 | 7.08 |
| stopping distance, m | 7.2 | 7.2 | 7.3 | 8.5 | 9.3 |

`TyreVehicleController` runs `TyreProfile.substeps × √pace` spin steps for the wheel's share.

At 2.0: 80 kph from rest in about 2.8 s, 152 kph after 8 s, limiter 198 kph (140 × √2). Given up
knowingly: the countersteered slide (`hold`) lasts 0.68 / 0.83 / 3.57 s at 42 / 63 / 86 kph, where
pace 1.5 held 1.93 / 3.53 / 3.47 s. With `skills.tres`'s `drift_min_s` at 0.5 s (`Q172`) every row
still pays.

Sweep with `tools/skidpad.sh --sweep=pace.pace_scale=`, which re-fits the car and scales
`--entry-kph` by the root.
