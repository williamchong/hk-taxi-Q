# handbrake.tres

Rationale for `game/tuning/systems/handbrake.tres`. Each heading is the line the block sat above; `Overview` is
the file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The drift button's handbrake: a torque on each rear wheel, as a real car's.

⚠️ The sections below moved here from `tyre.md` when the dials became the car's systems (`Q155`,
2026-10-05); their prose keeps the names the dials had when it was written: `handbrake_torque_nm` → `torque_nm`.

## `torque_nm = 1150.0`

**1,150 since 2026-10-05**, with stability control's slip cut from 10° (`stability_control.md`
has the table): about 1.08 × the rear wheels' lock on the real taxi (≈ 1,060 N·m), so the button
still locks them. Swept 1,000 / 1,150 with the cut from 10°: the tap at 86 kph 21.1 / 37.3°
(87.6° at 1,275), 63 kph 20.0 / 23.6°, 42 kph unmoved (70.9 / 69.2°); 1,000 drops the
countersteered `turn` at 86 to 54° and the tap's slide under a start at 63 / 86, so 1,150.

The section below is the value as first set, at 1,275.

About 1.2 × the rear wheels' lock on the real taxi (`Q153`): 1,400 kg at `gravity_scale` 1.0 on
0.31 m wheels, capacity ≈ 3,430 N × 0.31 m ≈ 1,060 N⋅m per wheel. It was 1,250 on the 1,200 kg car
with 0.35 m wheels (capacity ≈ 1,030). At gravity 1.6 it was 2,000 (capacity ≈
1,650), kept there on the user's call as 1.2 ×, the gentle end of a
rally hydraulic handbrake, which is built to lock the rears at once with margin (kept on the
user's call after asking). Swept 1,000 / 1,500 / 2,000 at `mu` 1.0, gravity 1.6 and
twice today's drive (2026-10-05): the tap peaks 69 / 62 / 53° at 42 kph and 47–48° at 63 at all
three; 2,000 is the only value bringing the countersteered `turn` out inside 80–110° at both 42 and
63 kph (100 / 96°; 158 / 70° at 1,000) and gives `hold` 3.40 / 3.12 s there. At 3,000 the tap
spins at 63 and 86 (164 / 168°).

At `mu` 2.0 it was 3,000 (capacity ≈ 3,300 N⋅m): swept 1,500–4,000 on `hold`, 3,000 the best at 63
kph, 4,000 killed the slide there and helped it at 86.
