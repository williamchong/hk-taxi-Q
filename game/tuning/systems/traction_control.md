# traction_control.tres

Rationale for `game/tuning/systems/traction_control.tres`. Each heading is the line the block sat above; `Overview` is
the file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

A real car's traction control: a driven wheel's torque is cut once it spins past the tyre's grip. Drift mode stands it down for a slide the player asked for (`drift_mode.md`).

⚠️ The sections below moved here from `tyre.md` when the dials became the car's systems (`Q155`,
2026-10-05); their prose keeps the names the dials had when it was written: `traction_limit` → `wheelspin_limit`.

## `wheelspin_limit = 1.0`

Traction control cuts a driven wheel's torque past peak wheelspin, so full throttle at full lock
grips (peak slip 2.5° where it was 82° without it). Forward slip only: keyed on the combined slip
it cut the drive at every cornering limit.
