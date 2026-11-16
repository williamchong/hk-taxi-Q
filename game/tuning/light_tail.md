# light_tail.tres

Rationale for `game/tuning/light_tail.tres` (`Q119`).

The light tail (`P3-70`, `Q158`): once a slide has paid, each tail lamp leaves a streak along the
arc it swings through, fading with age. `LightTail` (`scripts/vehicle/light_tail.gd`) finds the two
brake lenses in the body mesh, `LightTrail` lays the streak as a ring of pieces, and
`light_tail.gdshader` fades each against the clock it was laid at.

The tail lays from `PAID_TIER` of `SkillTracker.drift_tier`, the slide's first award, so a streak
is always a paid one (the user's call). The sparks show the counting tier.

Every key is required: `light_tail_profile.gd` declares no defaults, and the rig refuses a zero or
empty `colours` (`LightTail.usable`). `verify_vehicle.gd` asserts the scene hands the rig this
file. The ring's capacity is not a key: `LightTail.capacity_for` derives it from `life_s`.

Provisional: set by eye; the user's look call is owed.

- `colours`: one entry, the brake lens's lit red (`make_vehicle.py`'s `RED`, peak-normalised), so
  every tier streaks the same. A colour per tier from `PAID_TIER`, the last kept past the end,
  as `drift_sparks.tres`.
- `life_s` 0.4: how long a piece lives; the tip is about 4 m back at a slide's 40 kph sideways.
- `fade_power` 1.0: linear. Above 1 it drops sooner and lingers faint.
- `max_step_m` 2.0: `skid_marks.tres`'s reason. A fast slide is unbroken; a teleport or reset
  starts a new streak.
- `width_scale` 1.0: the streak's cross-section is the lens's own box, a cross of two quads.
