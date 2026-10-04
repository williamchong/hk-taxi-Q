# drift_sparks.tres

Rationale for `game/tuning/drift_sparks.tres`. Each heading is the line the block sat above; `Overview` is
the file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The drift's sparks (`P3-58`): whether the slide counts, and for how long. `DriftSparks`
(`scripts/vehicle/drift_sparks.gd`) shows `SkillTracker.drift_tier` — -1 with no slide at the
threshold, 0 while one counts toward `skills.tres`'s `drift_min_s`, then how many awards it has
paid — handed in by `TaxiHire` off `FareSystem.drift_tier_changed`. The meter that pays is the
meter that lights them, so the sparks and the receipt cannot disagree. 🚫 No boost: Mario Kart's
legibility, not its control (`Q153`).

⚠️ EVERY KEY BELOW IS REQUIRED. `drift_sparks_profile.gd` declares no defaults, so a missing key reads
as zero and an empty `colours` as no tiers, and the rig refuses to light on either
(`DriftSparks.usable`). `spread_deg` may legally be 0. `verify_vehicle.gd` asserts the scene hands
the rig this very file, the colour per tier and a refused empty table; `verify_fares.gd`'s
`sparks:` block steps the tier on the tracker.

Provisional: the colours and the tier count are the user's pick from rendered frames (`P3-58`).

## `colours = PackedColorArray(…)`

Index by tier, the last kept past the end:

- `[0]` warm white `(1, 0.95, 0.8)` — the slide is at the threshold and counting toward its first
  award. Shown, so a player learns the angle before the money; an alpha of 0 here would hide it.
- `[1]` blue `(0.3, 0.6, 1)` — paid once, at `drift_min_s`.
- `[2]` orange `(1, 0.55, 0.1)` — paid twice.
- `[3]` purple `(0.8, 0.35, 1)` — three and on.

Blue, orange, purple is Mario Kart's order, which a player already reads as "longer".

## `amount = 24`

Sparks alive per rear wheel: a spray, not a fountain. Fill rate is a handset's cost (`P0-3b`).

## `lifetime_s = 0.35`

## `speed_mps = 4.0`

## `spread_deg = 25.0`

About 1.4 m of flight off the tyre, back and up, falling: a short spray that stays near the car
rather than painting the street.

## `length_m = 0.12`

## `thickness_m = 0.02`

A streak, stretched along its flight (`particle_flag_align_y`).

## `burst_s = 0.3`

## `burst_scale = 2.0`

On each step up the sparks double in size for a beat, so the award reads at the tyre as well as
under the clock.
