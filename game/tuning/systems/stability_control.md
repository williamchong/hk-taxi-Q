# stability_control.tres

Rationale for `game/tuning/systems/stability_control.tres`. Each heading is the line the block sat above; `Overview` is
the file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

Stability control's power cuts (a real car's ESC takes engine torque away when the car runs wide or its tail swings out). Power only: a real ESC also brakes single wheels, which this does not model.

⚠️ The sections below moved here from `tyre.md` when the dials became the car's systems (`Q155`,
2026-10-05); their prose keeps the names the dials had when it was written: `turn_drive_cut` → `understeer_power_cut`, `slide_drive_fade_from_deg` / `_to_deg` → `slip_power_cut_from_deg` / `_to_deg`, `assist_drive_fade_from_deg` → `assisted_slip_cut_from_deg`.

## `understeer_power_cut = 0.5`

The share of the forward drive taken off at full lock while traction control is armed (`P3-55`,
`Q153`), for the power-on corner: at 0 a full-lock corner under the doubled drive runs to about
128 kph from any entry and its arc widens, where the shipped car settles at 62–65. The drift button
disarms traction control, so a slide never sees it — `ride` and `hold` hold their peak and
`longest` at every value, and only the exit after the re-arm moves. Swept 0–0.9 on `corner` at 42 /
63 / 86 / 105 / 125 kph (`Q153` holds the table): 0.5 settles near 90 kph and pulls away from
10 kph at full lock as the shipped car does (45.1 against 43.3 kph two seconds in); 0.6 settles
near 70 and 0.7 near 57, the shipped car's terminal speed between them, pulling away 13% and 30%
behind it. Set at 0.5 on the user's call after driving the pad (2026-10-02, "seems ok for now"):
the arc stops widening and the pull-away is the shipped car's; 0 turns it off. 🔴 Graded on `corner` and
`liftoff`'s windows across entries and on the 10 kph pull-away, never on `hold` or `ride`, which
cannot see it.

## `slip_power_cut_from_deg = 10.0`, `slip_power_cut_to_deg = 40.0`

**From 10° since 2026-10-05** (the user's "tune the aids so the plain tap stops spinning"): on the
real taxi's power (`Q153`, 6,000 N off the line, 83 kW above) a plain tap with the assist off
spun at 42 and 86 kph. Swept one lever at a time at three speeds: the cut's start was the only
lever that reached 42 kph (10 / 15 / 20° → tap 67.7 / 110.4 / 163.4° there) — `drift_side_cut`
0.3 / 0.45, `rev_limiter.overspeed_share` 0 / 0.25 and the handbrake left it at 163° — so the
spin there is power feeding the slide, not the rear's grip. The end stays at 40°: 20 / 25 / 30°
collapse `hold` at 42 kph (0.68 / 0.78 / 0.92 s) and leave 86 kph at 75–81°. The handbrake
(`handbrake.md`) finished 86 kph. The assisted mode starts at its own 35° and is not moved.

| 42 / 63 / 86 kph, assist off | before | cut from 10° | + handbrake 1,150 |
|---|---|---|---|
| `tap` peak | 163.3 / 64.5 / 162.9° | 67.7 / 29.8 / 87.6° | 69.2 / 23.6 / 37.3° |
| `hold` longest | 3.30 / 3.12 / 2.93 s | 2.07 / 3.12 / 2.88 s | 2.08 / 2.82 / 2.98 s |
| `ride` longest | 3.30 / 2.35 / 3.47 s | 1.47 / 1.95 / 2.77 s | 1.50 / 2.82 / 2.30 s |
| `turn@counter` came out | 178.2 / 154.8 / 138.6° | 109.8 / 67.6 / 133.7° | 117.8 / 61.1 / 120.6° |

The section below is the band as first set, at 25°.

The forward drive fades out over this band of body slip while traction control is disarmed, so a
held throttle cannot spin the car (`Q153`, the user's street report). A plain held tap peaked 30.7 /
47.8 / 65.1 / 49.7 / 50.0° at 42 / 50 / 63 / 75 / 86 kph; with the band and the cut ending at 65 kph,
29.0 / 35.7 / 41.6 / 35.3 / 34.5°. `hold` never reaches the band (peak 23–27°) and is unchanged, as
is the `turn` row at 42 kph. 30 → 40–50 left 63 kph at 50–53°; no existing dial did it
(`rim_overspeed` 0 calms 75–86 kph and loses `hold` at 86; `traction_rearm_s` moves nothing).

## `assisted_slip_cut_from_deg = 35.0`

Where the slide's drive fade starts while the drift assist is on, in place of
`slide_drive_fade_from_deg` (25). At 25 the assisted slide at 86 kph lost its drive at 1.40 s, under
`drift_min_s`; 30° 1.58 s, 32° 3.17 s (a cliff, so 35 sits past it), 35° 3.17 s, with 42 / 63 kph
unmoved. Moved for everyone, 35° raised a plain tap's peak 41.6 → 49.3° at 63 kph and left `turn`
and `hold` identical; kept to the assist on the user's call (2026-10-05), so the off mode keeps the
calmer rear. Refuted at 86 first: the share, `countersteer_lock_deg`, `drift_side_cut_to_kph`,
`turn_drive_cut`, `traction_rearm_s`, `side_force_depth`; `rim_overspeed` 0 works and loses `hold`
(`Q153`).
