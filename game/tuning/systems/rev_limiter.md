# rev_limiter.tres

Rationale for `game/tuning/systems/rev_limiter.tres`. Each heading is the line the block sat above; `Overview` is
the file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

A real engine's cut-out, here on the driven wheels' rim speed.

⚠️ The sections below moved here from `tyre.md` when the dials became the car's systems (`Q155`,
2026-10-05); their prose keeps the names the dials had when it was written: `rim_overspeed` → `overspeed_share`.

## `overspeed_share = 0.5`

⚠️ Set while the drive was sized on the car's speed, so a rim past the road's speed was handed
more power than the engine has. Since 2026-10-06 (`Q153`) the drive is sized on the rim's own
speed and falls as it spins up; this value has not been re-swept on that.

How far past top speed a driven wheel's rim may spin before the drive is stopped, as a share of it
(`P3-53`, `Q153`). At 0 the limiter sits at 140 kph of rim speed and a countersteered slide at
86 kph meets it mid-slide: `hold` 1.40 s. At 0.5, `hold` reads 1.93 / 2.63 / 3.17 s at 42 / 63 /
86 kph and every bar but the assisted slide at 42 kph (1.92 s) passes; the cost is a plain input's
peak, 28–30° → 48–52° against the 60° bar. 0.25 does not carry 86 kph (1.62 s). `Q153` holds the
grid with `handbrake_torque_nm`. Set at 0.5 on the user's call after driving the pad (2026-10-02,
"seems ok for now"); 0 is today's limiter.
