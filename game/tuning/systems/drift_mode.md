# drift_mode.tres

Rationale for `game/tuning/systems/drift_mode.tres`. Each heading is the line the block sat above; `Overview` is
the file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

A real car's drift mode, switched by the driver's hand: traction control and stability control's understeer cut stand down from the drift button's press, or a flick (`arcade_aids.md`), until the slide is over (`DriftMode`).

⚠️ The sections below moved here from `tyre.md` when the dials became the car's systems (`Q155`,
2026-10-05); their prose keeps the names the dials had when it was written: `traction_rearm_s` → `rearm_s`, "traction control off" → drift mode engaged.

## `rearm_s = 2.0`

The drift button switches traction control off; it re-arms once the button has been up this long
and the body's slip is under the game's 14°. At 0 and 0.5 it re-armed before the throttle took the
slide over (`hold` at 63 kph 0.00 s). At 1.0 a player's own input — the tap, the steering and the
throttle held (`ride`) — slid 0 s at 42 kph, because the governor came back and cut the power the
slow slide needed; at 2.0 it slides 1.85 s. 3.0 reads the same as 2.0.

## `rearm_on_steer_release = true`

Graded with the rear side cut, the same round: see `arcade_aids.md`, `drift_side_cut`.
