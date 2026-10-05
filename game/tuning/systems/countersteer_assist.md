# countersteer_assist.tres

Rationale for `game/tuning/systems/countersteer_assist.tres`. Each heading is the line the block sat above; `Overview` is
the file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

A real car's countersteer assist (electric steering nudging into opposite lock, as VW's DSR or Lexus's VDIM do): the player's option `drift_assist` (`P3-56`), on by default in the game and off on the pads (`--assist=on`).

⚠️ The sections below moved here from `tyre.md` when the dials became the car's systems (`Q155`,
2026-10-05); their prose keeps the names the dials had when it was written: `countersteer_assist` → `gain`, `countersteer_lock_deg` → `max_lock_deg`.

## `gain = 1.5`

The share the drift assist turns the fronts by, while the player's option is on (`P3-56`,
`Q153`: default on, the floor a novice's slide pays from). Off, countersteering is the player's
skill — the user's call of 2026-09-29 ("i want counter steering to be part of gameplay") is the off
mode, not reversed. 🔴 With the option off the `ride` row is *meant* to fall short of the fare's
bar; the countersteered `hold` row is the one that pays. With it on, `ride` is the row, and `hold`
must read as it does off: a player who countersteers is not fought.
The assist acts only while the player steers INTO the slide (`_update_steering`): still turning the
fronts after a let-go or a countersteer, it brought the 90° `turn` out at 58–75°; gated, `turn` is
byte-identical in both modes. And once the player countersteers, it stands aside until the slide is
over (`assist_yields`, the slip back under the tyre's peak): re-tested each tick, it stepped back in
every time the pad's feathering driver crossed zero, and `hold` read 0.27 / 0.27 / 1.05 s at 42 /
63 / 86 kph. Latched, 2.00 / 3.28 / 1.45 s — the off mode's 2.00 / 3.28 at 42 and 63, every other
row in both modes byte-identical. 86.48 kph sits on `hold`'s own cliff (`Q153`): across 76–95 kph
the two modes read within 0.1 s, about 3.1 s to 83 kph and about 1.4 s from 90, and only the
step's place differs. Graded 2026-10-05, `--assist=on`, three identical runs a cell:

| entry kph | `ride` longest, off / on | `ride` peak, off / on |
|---|---|---|
| 42 | 0.85 / 3.30 s | 29.0 / 26.0° |
| 63 | 0.80 / 3.32 s | 41.6 / 33.8° |
| 86 | 1.12 / 3.17 s | 34.5 / 39.4° |

2.0–3.0 straightens the slide at every speed (86 kph 0.73 s at 2.0). The history below is from
before the call that made it an option.

Before: off, on the user's call after driving the pad by hand (2026-09-29): countersteering is the
player's skill, not the car's. The mechanism stays in
`TyreVehicleController._update_steering` behind the zero: while the car slides past the tyre's
peak, the fronts would turn towards the travel by this share of the excess. Swept on `ride` before
the call: 0 → 1.5 took 63 kph from 1.43 to 2.60 s above 14° and 86 kph from 1.57 to 3.22 s with the
peak under 40°; 1.0 and 1.25 peaked near 50°. At 1.5 a plain held input held 1.85 / 2.55 / 3.15 s at
42 / 63 / 86 kph, where `hold`'s scripted driver, countersteering on top of it, killed the slide
(0.13 s). At 0, graded the same day:

| entry kph | `ride` longest | `ride` peak | `hold` longest | `hold` peak |
|---|---|---|---|---|
| 42 | 1.63 s | 28.0° | 1.87 s | 25.8° |
| 63 | 1.60 s | 28.5° | 2.55 s | 24.9° |
| 86 | 1.68 s | 30.3° | 1.40 s | 27.5° |

A plain input does not reach the fare's first payment (`drift_min_s` 2.0 s); a player who
countersteers does at 63 kph — the design. Both rows grade this car now. Open: `hold` at 86 kph
(1.40 s) sits under the bar. The handling table's speed-narrowed steering lock was the suspect and
is refuted (`slide_lock_deg` below).

## `max_lock_deg = 35.0`

Inert while the drift assist is off. Swept 15–60 with it on: flat at 42 / 63 kph and 1.38–1.40 s at
86 under the plain fade band. How far the fronts may turn while the assist
countersteers, where the handling table narrows the player's lock with speed (16.4° at 63 kph). A
slide of 37° needs a front wheel near that angle to point along the travel.
