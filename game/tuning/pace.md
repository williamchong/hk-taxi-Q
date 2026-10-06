# pace.tres

Rationale for `game/tuning/pace.tres`. Each heading is the line the block sat above; `Overview` is
the file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The game's pace as one named scale (`Q156`, 2026-10-06), for every car alike. The world is scaled,
never the car: gravity is multiplied by `pace_scale` and every force the car makes follows it
(`PaceProfile` lists what takes the scale, its root, or nothing). That is the real car on a road
where everything happens `√pace_scale` times as fast — the same corner at the same angles and the
same share of each tyre's grip, taken that much quicker.

Why a scale and not grip: the car `426f5a0` shipped was fun for its envelope (`mu` 2.0 under 1.6×
gravity, twice the drive: 3.2 g of cornering), and that envelope was thirty hand-sized numbers. At
3.2 g a lift or a feint never moved the rear (`tyre.md`); at a real tyre's 1.0 it does. The pace
buys the envelope back without touching the tyre: one made-up number, named, where there were
thirty.

🔴 **The scaling is exact, and measured so** (2026-10-06, `--sweep=pace.pace_scale=`, which
re-fits the car and scales `--entry-kph` by the root): at pace 4 on a 120 Hz tick — the same
ticks per scaled second as pace 1 at 60 — the brake from 84 kph reads 36.48 m/s² over 7.2 m
against pace 1's 9.12 over 7.2 from 42, the coast 37.5 m against 37.5, and the corner's rears
0.59× their grip against 0.61×.

🔴 **At the project's 60 Hz it holds to pace 2.0 and not to 2.5.** The brake is the instrument
(four times pace 1's deceleration over the same metres, from the same speed in the car's terms):

| pace | 1.0 | 1.5 | 2.0 | 2.5 | 4.0 |
|---|---|---|---|---|---|
| brake from 42 kph × root, m/s² ÷ pace | 9.12 | 9.16 | 9.06 | 7.86 | 7.08 |
| stopping distance, m | 7.2 | 7.2 | 7.3 | 8.5 | 9.3 |

Past 2.0 the tick is too coarse for the wheels and springs (the corner's rear load swings 0.56
of the axle's where 0.29 is right): a pace over 2 wants a faster physics tick, not a dial.
`TyreVehicleController` runs `TyreProfile.substeps × √pace` spin steps for the part of this that
is the wheel's (pace 2's brake 17.4 → 18.1 m/s² of the 18.2 that is exact).

⚠️ **What does not scale is the player.** Every dial in seconds that is an INPUT stays in
seconds (`steer_attack_s`, the flick's windows as the hand makes them, the pad's own driver); the
systems' own clocks (`drift_mode.rearm_s`, the catch limiter's window and rate, the drift
button's ramp) run at the pace. So a slide at pace 2 is the pace-1 slide in 0.71 of the seconds,
with the same hands: the drift is as readable as the pace is low, and that is the trade the dial
makes.

## `pace_scale = 1.5`

**1.5 since 2026-10-06, provisional until the user's drive** (`Q156`; the dial itself shipped at
1.0, every pad row byte-identical with the car before it). Read off the pad at REAL entry speeds
of 42 / 63 / 86 kph, the yaw brake in and `drive_boost` gone:

| | pace 1.0 (with the boost) | **pace 1.5** | pace 2.0 |
|---|---|---|---|
| `turn@off` came out (bar 80–110° at 42 / 63) | 95 / 118 / 110° | **91 / 97 / 110°** | 81 / 84 / 93° |
| `turn@lift` came out | 86 / 100 / 81° | **86 / 87 / 94°** | 81 / 82 / 82° |
| `hold` longest (bar 2 s at 63 / 86) | 3.52 / 3.35 / 2.13 s | **1.93 / 3.53 / 3.47 s** | 0.68 / 0.83 / 3.57 s |
| `ride` longest (bar: under 2 s) | 1.20 / 1.70 / 1.73 s | **0.88 / 1.08 / 1.38 s** | 0.98 / 0.87 / 0.98 s |
| `tap` peak (bar: over 14°) | 34.1 / 26.5 / 26.8° | **39.0 / 32.4 / 27.0°** | 48.0 / 40.9 / 31.8° |
| speed after 4 / 8 s of throttle | 68 / 108 kph | **80 / 122 kph** | 102 / 152 kph |

1.5 is the highest pace that keeps the countersteered slide at 63 kph: at 2.0 that speed is the
car's own 45, where the slide is its low end's (`hold` 0.83 s). It is quicker off the line with no
boost than pace 1 was with it, and it is the first table on which every `turn` row at all three
speeds is inside 80–110°. What it gives up: the slide is shorter in seconds (`ride` 1.20 → 0.88 s
at 42), and `hold` at 42 kph sits just under the fare's 2 s. The limiter is 171 kph (140 × √1.5).
🔴 A feel value: the pad says which paces break a bar, the drive says which one is fun.
1.0 is a real road; `426f5a0`'s cornering envelope would be about 3.2, which 60 Hz cannot hold.
