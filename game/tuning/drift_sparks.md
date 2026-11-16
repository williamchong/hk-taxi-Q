# drift_sparks.tres

Rationale for `game/tuning/drift_sparks.tres` (`Q119`).

The drift's sparks (`P3-58`). `DriftSparks` (`scripts/vehicle/drift_sparks.gd`) shows
`SkillTracker.drift_tier`: -1 with no slide at the threshold, 0 while one counts toward
`skills.tres`'s `drift_min_s`, then the number of awards paid. The meter that pays lights them. No
boost (`Q153`).

Every key is required: `drift_sparks_profile.gd` declares no defaults, and the rig refuses to light
on a zero or on empty `colours` (`DriftSparks.usable`). `spread_deg` may be 0. `verify_vehicle.gd`
asserts the scene hands the rig this file.

- `colours`, by tier, the last kept past the end: warm white (counting toward the first award,
  shown so the player learns the angle), blue (paid once), orange (twice), purple (three and on).
  Mario Kart's order. Provisional: the user's pick from frames.
- `amount` 24: sparks alive per rear wheel. Fill rate is a handset cost (`P0-3b`).
- `lifetime_s` 0.35, `speed_mps` 4.0, `spread_deg` 25: about 1.4 m of flight off the tyre, back
  and up; a short spray near the car.
- `length_m` 0.12, `thickness_m` 0.02: a streak along its flight (`particle_flag_align_y`).
- `burst_s` 0.3, `burst_scale` 2.0: on each step up the sparks double in size for a beat.
