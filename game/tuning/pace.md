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

## `pace_scale = 1.0`

A real road. The dial shipped at 1.0 with every pad row at 42 / 63 / 86 kph byte-identical to
the car before it; the value the game plays at is a graded change of its own.
